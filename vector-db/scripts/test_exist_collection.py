import os
import sys

from dotenv import load_dotenv
from qdrant_client import QdrantClient


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

collection_name = os.getenv("QDRANT_COLLECTION")

exists = client.collection_exists(collection_name)

print("Collection:", collection_name)
print("Exists:", exists)
