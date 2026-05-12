"""
Pattern Mirror — RAG pipeline.

Semantic framework search using ChromaDB + sentence-transformers.
Replaces the exact-key lookup_framework tool with vector similarity search —
Claude describes the pattern in natural language, we find the closest match.

Entry points:
  search_frameworks(query, n_results=2) → list[dict]   — search and return formatted content
  build_index()                                         — build or verify the index (idempotent)
"""

import json
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

FRAMEWORKS_PATH = Path(__file__).parent / "frameworks.json"
DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "frameworks"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ── Collection access ────────────────────────────────────────

def _get_collection() -> chromadb.Collection:
    """Get or create the ChromaDB collection with sentence-transformer embeddings."""
    client = chromadb.PersistentClient(path=str(DB_PATH))
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


# ── Index build ──────────────────────────────────────────────

def build_index() -> None:
    """Build the framework index from frameworks.json. Idempotent — skips if already built.

    Called lazily on first search. Safe to call on every startup.
    Documents are embedded as: name + tradition + description + pattern_tags.
    Full framework content is stored in metadata for retrieval without re-reading the file.
    """
    collection = _get_collection()
    if collection.count() > 0:
        return  # already indexed

    with open(FRAMEWORKS_PATH) as f:
        frameworks = json.load(f)

    documents, ids, metadatas = [], [], []

    for key, fw in frameworks.items():
        # Rich text for embedding — covers name, tradition, description, and tags
        embed_text = (
            f"{fw['name']} ({fw['tradition']})\n"
            f"{fw['description']}\n"
            f"Pattern tags: {', '.join(fw['pattern_tags'])}"
        )
        # Full formatted content stored in metadata — returned directly to Claude
        full_content = (
            f"Framework: {fw['name']} ({fw['tradition']})\n"
            f"Description: {fw['description']}\n"
            f"Protocol note: {fw['protocol_note']}\n"
            f"Pattern tags: {', '.join(fw['pattern_tags'])}"
        )
        documents.append(embed_text)
        ids.append(key)
        metadatas.append({
            "content": full_content,
            "name": fw["name"],
            "tradition": fw["tradition"],
        })

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    print(f"✅  Framework index built: {len(ids)} frameworks indexed.")


# ── Search ───────────────────────────────────────────────────

def search_frameworks(query: str, n_results: int = 2) -> list[dict]:
    """Semantic search for the most relevant psychological frameworks.

    Builds the index on first call if not yet indexed.
    Returns a list of dicts with 'key' and 'content' fields.
    Content is pre-formatted for direct inclusion in Claude's context.

    n_results capped at collection size to avoid ChromaDB errors on small collections.
    """
    collection = _get_collection()
    if collection.count() == 0:
        build_index()
        collection = _get_collection()

    n = min(n_results, collection.count())
    results = collection.query(query_texts=[query], n_results=n)

    output = []
    for key, metadata in zip(results["ids"][0], results["metadatas"][0]):
        output.append({
            "key": key,
            "content": metadata["content"],
        })
    return output
