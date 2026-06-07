"""
Chunking strategy comparison for The Unofficial Guide — Boston food reviews.

Stretch feature: test 2+ chunking approaches on the same query set and report
which performed better and why.

What it does:
  - Builds chunk sets under several chunking strategies (target / max / overlap)
  - Embeds each set with all-MiniLM-L6-v2 into its own ChromaDB collection
  - Runs the 5 evaluation questions (from planning.md) against each strategy
  - Scores retrieval objectively, isolated from the LLM:
      * hit@k  : did the top-k include a chunk from an expected source file?
      * MRR     : 1/rank of the first correct-source chunk (0 if none)
      * avg_sim : mean cosine similarity of the top-k chunks to the query
  - Prints a comparison table and writes chunking_comparison.md

Run:
  python src/compare_chunking.py

No Groq key required — this measures retrieval quality, which is what chunking
actually controls. Answer generation adds LLM variance that would muddy the
comparison, so it is intentionally excluded.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import build_chunks

EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5
DOCS_DIR = Path("documents")
CHROMA_DIR = "chroma_db_compare"  # separate store; does not touch the app's index

# --- Strategies to compare: (name, target, max_size, overlap) ---
STRATEGIES = [
    ("baseline_600_100", 600, 750, 100),   # planning.md spec, sentence-aware
    ("small_300_50", 300, 400, 50),         # tighter chunks, more of them
    ("large_1000_150", 1000, 1200, 150),    # fewer, broader chunks
]

# --- Evaluation set: each question + the source file stems that should
#     contain the answer (derived from planning.md's Evaluation Plan and the
#     documents/ folder). A retrieval is a "hit" if any top-k chunk comes
#     from one of these sources. ---
EVAL = [
    {
        "q": "What do reviewers say about the wait time at Mike's Pastry in the North End?",
        "expected": {"bostonmagazine_northend_pastry", "sample_reddit_northend"},
    },
    {
        "q": "Which neighborhood do reviewers recommend for the best ramen in Boston?",
        "expected": {"reddit_bostonfood_ramen", "thefoodlens_allston_cambridge_eats",
                     "bostonfoodtruckblog_allston"},
    },
    {
        "q": "According to reviews, is Neptune Oyster worth the price for its lobster roll?",
        "expected": {"yelp_neptune_oyster_reviews", "eater_boston_seafood_guide"},
    },
    {
        "q": "What do reviewers recommend for budget-friendly eats in Chinatown?",
        "expected": {"thefoodlens_chinatown_budget", "yelp_gourmet_dumpling_reviews",
                     "boston_com_chinatown_openings"},
    },
    {
        "q": "Do reviews recommend any good vegetarian or vegan restaurants in Cambridge?",
        "expected": {"popbopshop_cambridge_vegetarian", "thefoodlens_allston_cambridge_eats",
                     "confessions_chocoholic_cambridge_dessert"},
    },
]


def build_collection(client, model, name, target, max_size, overlap):
    """Chunk the corpus with one strategy and index it into a fresh collection."""
    chunks = build_chunks(DOCS_DIR, target=target, max_size=max_size, overlap=overlap)
    try:
        client.delete_collection(name)
    except Exception:
        pass
    coll = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
    texts = [c.text for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    coll.add(
        ids=[f"{c.source}-{c.chunk_index}" for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"source": c.source} for c in chunks],
    )
    char_lens = [c.char_len for c in chunks]
    stats = {
        "n_chunks": len(chunks),
        "avg_chars": sum(char_lens) / len(char_lens) if char_lens else 0,
    }
    return coll, stats


def evaluate(coll, model, k=TOP_K):
    """Run the eval set against one collection; return per-strategy metrics."""
    hits = 0
    mrr_total = 0.0
    sim_total = 0.0
    sim_count = 0
    per_q = []
    for item in EVAL:
        q_emb = model.encode([item["q"]]).tolist()
        res = coll.query(query_embeddings=q_emb, n_results=k,
                         include=["metadatas", "distances"])
        sources = [m["source"] for m in res["metadatas"][0]]
        sims = [1.0 - d for d in res["distances"][0]]  # cosine sim from distance
        sim_total += sum(sims)
        sim_count += len(sims)

        rank = next((i + 1 for i, s in enumerate(sources) if s in item["expected"]), None)
        hit = rank is not None
        hits += int(hit)
        mrr_total += (1.0 / rank) if rank else 0.0
        per_q.append({"q": item["q"], "hit": hit, "rank": rank, "top_sources": sources})

    n = len(EVAL)
    return {
        "hit_rate": hits / n,
        "mrr": mrr_total / n,
        "avg_sim": sim_total / sim_count if sim_count else 0.0,
        "per_q": per_q,
    }


def main() -> None:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    model = SentenceTransformer(EMBED_MODEL)

    rows = []
    details = []
    for name, target, max_size, overlap in STRATEGIES:
        coll, stats = build_collection(client, model, name, target, max_size, overlap)
        metrics = evaluate(coll, model)
        rows.append((name, target, overlap, stats, metrics))
        details.append((name, metrics))
        print(f"\n[{name}]  chunks={stats['n_chunks']}  "
              f"avg_chars={stats['avg_chars']:.0f}  "
              f"hit@{TOP_K}={metrics['hit_rate']:.0%}  "
              f"MRR={metrics['mrr']:.3f}  avg_sim={metrics['avg_sim']:.3f}")

    write_report(rows, details)
    print(f"\nReport written to {Path('chunking_comparison.md').resolve()}")


def write_report(rows, details):
    best = max(rows, key=lambda r: (r[4]["hit_rate"], r[4]["mrr"], r[4]["avg_sim"]))
    lines = [
        "# Chunking Strategy Comparison",
        "",
        "Comparison of three chunking strategies on the same 5-question evaluation "
        "set, using identical embedding (all-MiniLM-L6-v2), vector store (ChromaDB, "
        "cosine), and top-k (5). Only the chunking parameters differ.",
        "",
        "## Method",
        "",
        "Each strategy re-chunks the full `documents/` corpus, embeds the chunks, and "
        "answers the five evaluation questions from `planning.md`. Because chunking "
        "controls *retrieval*, the metrics are retrieval-level and LLM-free:",
        "",
        "- **hit@5** — fraction of questions where a top-5 chunk came from a source "
        "file known to contain the answer.",
        "- **MRR** — mean reciprocal rank of the first correct-source chunk (rewards "
        "putting the right chunk higher).",
        "- **avg_sim** — mean cosine similarity of retrieved chunks to the query "
        "(how confident retrieval is).",
        "",
        "## Results",
        "",
        "| Strategy | Target/Overlap | Chunks | Avg chars | hit@5 | MRR | avg_sim |",
        "|----------|----------------|--------|-----------|-------|-----|---------|",
    ]
    for name, target, overlap, stats, m in rows:
        lines.append(
            f"| {name} | {target}/{overlap} | {stats['n_chunks']} | "
            f"{stats['avg_chars']:.0f} | {m['hit_rate']:.0%} | {m['mrr']:.3f} | "
            f"{m['avg_sim']:.3f} |"
        )
    lines += [
        "",
        f"**Winner: `{best[0]}`** — highest hit@5, with MRR and avg_sim as tie-breakers.",
        "",
        "## Why",
        "",
        "Smaller chunks (300 chars) produce more, tighter segments: each embedding "
        "represents a narrower idea, so similarity to a focused question is sharper "
        "and the right review is more likely to surface — but a single review's "
        "details (food + price + wait) can split across chunks, occasionally hurting "
        "recall. Larger chunks (1000 chars) capture whole discussions and rarely "
        "split a review, but mixing several restaurants into one embedding dilutes "
        "its relevance signal, lowering similarity and sometimes burying the "
        "on-topic chunk. The 600-char sentence-aware baseline sits between these: "
        "large enough to keep a typical short review intact, small enough to stay "
        "topically focused. The numbers above show which trade-off won on this "
        "review-heavy corpus.",
        "",
        "## Per-question retrieval (hit = correct source in top 5)",
        "",
    ]
    for name, m in details:
        lines.append(f"### {name}")
        lines.append("")
        for pq in m["per_q"]:
            mark = "✅" if pq["hit"] else "❌"
            rank = f"rank {pq['rank']}" if pq["rank"] else "not in top 5"
            lines.append(f"- {mark} {pq['q']} — {rank}")
        lines.append("")

    Path("chunking_comparison.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
