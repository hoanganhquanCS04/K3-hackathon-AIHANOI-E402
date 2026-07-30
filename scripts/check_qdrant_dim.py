"""Check Qdrant collection dim thuc te.

Doc env, connect Qdrant Cloud, in ra:
- dim, distance, point count
- payload indexes dang co
- so sanh voi OPENAI_EMBEDDING_DIMENSIONS

Lenh: uv run python scripts/check_qdrant_dim.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load env tu goc repo (cung vi tri ma code runtime dang dung).
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

url = os.getenv("QDRANT_URL")
api_key = os.getenv("QDRANT_API_KEY")
collection = os.getenv("QDRANT_COLLECTION") or "vlearn_transcripts_openai_small_768_v1"

if not url or not api_key:
    print("[FAIL] Thieu QDRANT_URL hoac QDRANT_API_KEY trong .env", file=sys.stderr)
    sys.exit(1)

client = QdrantClient(url=url, api_key=api_key, timeout=30)

print("=" * 60)
print("Kiem tra collection Qdrant")
print("=" * 60)
print(f"URL:         {url}")
print(f"Collection:  {collection}")
print(f"Configured:  OPENAI_EMBEDDING_DIMENSIONS = "
      f"{os.getenv('OPENAI_EMBEDDING_DIMENSIONS', '768')}")

try:
    info = client.get_collection(collection_name=collection)
except Exception as exc:
    print(f"[FAIL] khong get_collection duoc: {type(exc).__name__}: {exc}",
          file=sys.stderr)
    # Liet ke cac collection co san de biet collection that su ten gi
    try:
        all_cols = client.get_collections()
        print("\nCac collection dang co:", file=sys.stderr)
        for c in all_cols.collections:
            print(f"  - {c.name}", file=sys.stderr)
    except Exception:
        pass
    sys.exit(2)

vectors = info.config.params.vectors
size = getattr(vectors, "size", None)
distance = getattr(vectors, "distance", None)
count = client.count(collection_name=collection, exact=True).count

print(f"\nVector dim:   {size}")
print(f"Distance:     {distance}")
print(f"Point count:  {count}")

payload_schema = info.payload_schema or {}
print(f"\nPayload indexes ({len(payload_schema)}):")
if payload_schema:
    for name in sorted(payload_schema):
        print(f"  - {name}")
else:
    print("  (khong co index nao)")

expected = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "768"))
print(f"\nSo sanh:")
print(f"  collection dim hien tai: {size}")
print(f"  config muon dung:        {expected}")
if size == expected:
    print("  [OK] Khop nhau.")
else:
    print("  [WARN] KHONG khop — can doi env hoac rebuild collection.")