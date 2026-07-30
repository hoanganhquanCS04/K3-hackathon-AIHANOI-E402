"""Vector database pipeline for the VLearn transcript dataset."""

from vector_db.search import (
    find_chunks,
    find_sections,
    find_sessions,
    retrieve,
)
from vector_db.session_reader import (
    get_section_content,
    get_session_content,
    get_session_outline,
    get_session_sections,
)

__all__ = [
    "find_chunks",
    "find_sections",
    "find_sessions",
    "get_section_content",
    "get_session_content",
    "get_session_outline",
    "get_session_sections",
    "retrieve",
]


def main() -> None:
    """Print the package entry-point help."""
    print(
        "VLearn vector DB. Use `python -m vector_db.build`, "
        "`python -m vector_db.search`, or "
        "`python -m vector_db.session_reader`."
    )
