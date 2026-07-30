import os
import sys

from dotenv import load_dotenv
from qdrant_client import QdrantClient


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

url = os.getenv("QDRANT_URL")
api_key = os.getenv("QDRANT_API_KEY")

if not url:
    raise RuntimeError("Thiếu QDRANT_URL trong file .env")

if not api_key:
    raise RuntimeError("Thiếu QDRANT_API_KEY trong file .env")

client = QdrantClient(
    url=url,
    api_key=api_key,
    timeout=30,
)

collections = client.get_collections()

print("Kết nối Qdrant Cloud thành công.")
print(collections)
