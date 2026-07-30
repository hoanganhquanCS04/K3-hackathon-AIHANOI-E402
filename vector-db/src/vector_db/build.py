"""Build or rebuild the complete Qdrant vector database."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from qdrant_client import models

from vector_db.config import PROJECT_DIR, settings
from vector_db.embeddings import EmbeddingService
from vector_db.models import BuildSummary, PointDraft
from vector_db.parser import parse_all_transcripts
from vector_db.point_builder import (
    SCHEMA_VERSION,
    build_point_drafts,
)
from vector_db.qdrant_store import (
    PAYLOAD_INDEXES,
    QdrantStore,
    make_point_id,
)
from vector_db.validation import (
    validate_point_drafts,
    validate_sessions,
)

PARENT_EMBEDDING_STRATEGY = "normalized_mean_of_child_vectors_v1"


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(
    *,
    drafts: tuple[PointDraft, ...],
    sessions,
    exact_count: int | None,
    embedding_usage: dict,
    dry_run: bool,
) -> Path:
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = settings.artifact_dir / (
        "manifest.dry-run.json" if dry_run else "manifest.json"
    )
    counts = Counter(draft.point_type for draft in drafts)
    lock_path = PROJECT_DIR / "uv.lock"
    manifest = {
        "collection_name": settings.qdrant_collection,
        "schema_version": SCHEMA_VERSION,
        "embedding": {
            "provider": "openai",
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
            "encoding_format": "float",
            "distance": "cosine",
        },
        "point_counts": {
            "atomic_chunk": counts["atomic_chunk"],
            "section_parent": counts["section_parent"],
            "session_toc": counts["session_toc"],
            "total": len(drafts),
            "exact_collection_count": exact_count,
        },
        "session_count": len(sessions),
        "section_count": sum(len(session.sections) for session in sessions),
        "payload_indexes": sorted(PAYLOAD_INDEXES),
        "parent_embedding_strategy": PARENT_EMBEDDING_STRATEGY,
        "source": {
            "file_count": len(sessions),
            "source_hashes": {
                Path(session.metadata.source_file).name: (session.metadata.source_hash)
                for session in sessions
            },
        },
        "build": {
            "created_at": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "python_version": sys.version.split()[0],
            "uv_lock_hash": (_file_hash(lock_path) if lock_path.exists() else None),
            "dry_run": dry_run,
        },
        "embedding_usage": embedding_usage,
    }
    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_database(
    *,
    recreate: bool = False,
    dry_run: bool = False,
) -> BuildSummary:
    """Run the reproducible build pipeline."""

    print(f"Reading transcripts from: {settings.transcript_dir}")
    sessions = parse_all_transcripts()
    validate_sessions(sessions)
    drafts = build_point_drafts(sessions)
    validate_point_drafts(drafts, sessions)
    counts = Counter(draft.point_type for draft in drafts)
    print(
        "Validated source: "
        f"{len(sessions)} sessions, "
        f"{sum(len(s.sections) for s in sessions)} sections, "
        f"{counts['atomic_chunk']} atomic chunks"
    )

    if dry_run:
        manifest_path = _write_manifest(
            drafts=drafts,
            sessions=sessions,
            exact_count=None,
            embedding_usage={
                "model": settings.embedding_model,
                "dimensions": settings.embedding_dimensions,
                "api_requests": 0,
                "api_inputs": 0,
                "api_tokens": 0,
                "cache_hits": 0,
            },
            dry_run=True,
        )
        return BuildSummary(
            collection_name=settings.qdrant_collection,
            atomic_chunk_count=counts["atomic_chunk"],
            section_parent_count=counts["section_parent"],
            session_toc_count=counts["session_toc"],
            total_point_count=len(drafts),
            manifest_path=str(manifest_path),
        )

    direct_drafts = [
        draft for draft in drafts if draft.point_type in {"atomic_chunk", "session_toc"}
    ]
    with EmbeddingService() as embedder:
        direct_vectors = embedder.embed_many(
            (
                draft.logical_id,
                draft.embedding_text or "",
            )
            for draft in direct_drafts
        )
        vectors = dict(direct_vectors)
        for draft in drafts:
            if draft.point_type != "section_parent":
                continue
            vectors[draft.logical_id] = embedder.mean_normalized(
                vectors[child_id] for child_id in draft.child_chunk_ids
            )
        usage = embedder.usage_summary()

    points = [
        models.PointStruct(
            id=make_point_id(
                draft.point_type,
                draft.logical_id,
            ),
            vector=vectors[draft.logical_id],
            payload=draft.payload,
        )
        for draft in drafts
    ]

    store = QdrantStore()
    print(f"Ensuring collection: {store.collection_name}")
    store.ensure_collection(recreate=recreate)
    store.replace_sessions(session.metadata.session_id for session in sessions)
    print(f"Uploading {len(points)} points")
    store.upload_points(points)
    exact_count = store.exact_count()
    if exact_count != len(points):
        raise RuntimeError(
            f"Exact collection count mismatch: expected {len(points)}, "
            f"received {exact_count}"
        )

    manifest_path = _write_manifest(
        drafts=drafts,
        sessions=sessions,
        exact_count=exact_count,
        embedding_usage=usage,
        dry_run=False,
    )
    print(f"Build complete: {exact_count} points; manifest={manifest_path}")
    return BuildSummary(
        collection_name=settings.qdrant_collection,
        atomic_chunk_count=counts["atomic_chunk"],
        section_parent_count=counts["section_parent"],
        session_toc_count=counts["session_toc"],
        total_point_count=len(drafts),
        exact_collection_count=exact_count,
        manifest_path=str(manifest_path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the VLearn transcript vector database."
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate only the configured collection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without API calls or Qdrant writes.",
    )
    args = parser.parse_args()
    summary = build_database(
        recreate=args.recreate,
        dry_run=args.dry_run,
    )
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
