"""
Embedding and retrieval for The Unofficial Guide — Boston food & restaurant reviews.

Implements Milestone 4 from planning.md:
  - Load chunks from chunks.jsonl (produced by src/ingest.py)
  - Embed them with all-MiniLM-L6-v2 (sentence-transformers)
  - Store embeddings + metadata in a persistent ChromaDB collection
  - retrieve(query, k=5) returns the top-k chunks with a similarity score

Running this file embeds the chunks (once), then runs a query and prints the
top 5 chunks with their similarity score, source, and text.

Usage:
  python src/retrieve.py "best ramen in Boston"
  python src/retrieve.py            # uses a default demo query
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("chunks.jsonl")
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "boston_food"
EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5  # from planning.md "Retrieval Approach"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def load_chunks(path: Path = CHUNKS_FILE) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found. Run `python src/ingest.py` first.")
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def get_collection(reset: bool = False):
    """Return a ChromaDB collection configured for cosine similarity."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # so distance is cosine distance
    )


def build_index() -> None:
    """Embed all chunks and (re)load them into the ChromaDB collection."""
    chunks = load_chunks()
    collection = get_collection()

    # Rebuild only if the stored count does not match the chunk count.
    if collection.count() == len(chunks):
        return

    collection = get_collection(reset=True)
    model = get_model()

    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"source": c["source"], "path": c["path"]} for c in chunks],
    )
    print(f"Indexed {len(chunks)} chunks into ChromaDB collection '{COLLECTION_NAME}'.")


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """
    Return the top-k chunks for a query.

    Each result is a dict with: text, source, path, and score (cosine
    similarity in [0, 1], higher = more relevant).
    """
    collection = get_collection()
    query_emb = get_model().encode([query]).tolist()
    res = collection.query(
        query_embeddings=query_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    results: list[dict] = []
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    for doc, meta, dist in zip(docs, metas, dists):
        results.append(
            {
                "text": doc,
                "source": meta.get("source", "?"),
                "path": meta.get("path", "?"),
                "score": 1.0 - dist,  # cosine distance -> similarity
            }
        )
    return results


def print_results(query: str, results: list[dict]) -> None:
    print(f'\nQuery: "{query}"')
    print(f"Top {len(results)} chunks:\n" + "=" * 60)
    for rank, r in enumerate(results, 1):
        snippet = " ".join(r["text"].split())
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        print(f"\n#{rank}  score={r['score']:.3f}  source={r['source']}")
        print("-" * 60)
        print(snippet)


def main() -> None:
    query = " ".join(sys.argv[1:]) or "What do reviewers say about the wait at Mike's Pastry?"
    build_index()
    results = retrieve(query, k=TOP_K)
    print_results(query, results)


if __name__ == "__main__":
    main()
