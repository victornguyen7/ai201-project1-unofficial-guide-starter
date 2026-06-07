"""
Grounded generation for The Unofficial Guide — Boston food & restaurant reviews.

Implements Milestone 5 from planning.md:
  - Retrieve the top-k chunks for a question (src/retrieve.py)
  - Build a grounded prompt: the model answers ONLY from the retrieved
    context and attributes its claims to sources
  - Call the Groq API to generate the answer
  - Return the answer plus the list of sources it was drawn from

Grounding rules (enforced in the system prompt):
  - Use only the provided context. Do not use outside knowledge.
  - If the context does not contain the answer, say so plainly.
  - Note when reviews disagree rather than picking a single opinion.

Usage:
  python src/generate.py "What do reviewers say about the wait at Mike's Pastry?"

Requires GROQ_API_KEY in a .env file (see .env.example).
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from groq import Groq

from retrieve import retrieve, build_index, TOP_K

# A current Groq-hosted model. Swap if you prefer a different one.
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a Boston food and restaurant guide. You answer questions \
using ONLY the review excerpts provided in the context below.

Rules you MUST follow:
- Use only information in the provided context. Do not use any outside knowledge.
- If the context does not contain enough information to answer, say: "The available \
reviews don't cover that." Do not guess or invent details.
- These are subjective reviews. When sources disagree, say so and summarize the \
different opinions rather than presenting one as fact.
- Attribute claims to the sources they came from using the [source] labels given in \
the context (e.g., "according to [yelp_neptune_oyster_reviews]").
- Keep the answer concise and practical for someone deciding where to eat."""


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a labeled context block for the prompt."""
    blocks = []
    for c in chunks:
        text = " ".join(c["text"].split())
        blocks.append(f"[{c['source']}]\n{text}")
    return "\n\n".join(blocks)


def answer(question: str, k: int = TOP_K) -> dict:
    """
    Run the full RAG pipeline for one question.

    Returns {"answer": str, "sources": list[dict]} where each source has
    'source' and 'path'.
    """
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise SystemExit(
            "GROQ_API_KEY not set. Copy .env.example to .env and add your key."
        )

    build_index()  # no-op if the index is already built
    chunks = retrieve(question, k=k)
    if not chunks:
        return {"answer": "No documents are indexed yet.", "sources": []}

    context = build_context(chunks)
    user_prompt = (
        f"Context (review excerpts):\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, and attribute claims to their [source] labels."
    )

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,  # low: stay close to the source text
    )
    text = completion.choices[0].message.content.strip()

    # Deduplicate sources, preserving retrieval order.
    seen = set()
    sources = []
    for c in chunks:
        if c["source"] not in seen:
            seen.add(c["source"])
            sources.append({"source": c["source"], "path": c["path"]})

    return {"answer": text, "sources": sources}


def format_output(result: dict) -> str:
    """Produce the 'answer + source list' output format."""
    lines = [result["answer"], "", "Sources:"]
    for s in result["sources"]:
        lines.append(f"- {s['source']} ({s['path']})")
    return "\n".join(lines)


def main() -> None:
    question = " ".join(sys.argv[1:])
    if not question:
        question = "What do reviewers say about the wait at Mike's Pastry?"
    result = answer(question)
    print(format_output(result))


if __name__ == "__main__":
    main()
