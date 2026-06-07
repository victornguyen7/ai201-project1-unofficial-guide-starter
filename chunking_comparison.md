# Chunking Strategy Comparison

Comparison of three chunking strategies on the same 5-question evaluation set, using identical embedding (all-MiniLM-L6-v2), vector store (ChromaDB, cosine), and top-k (5). Only the chunking parameters differ.

## Method

Each strategy re-chunks the full `documents/` corpus, embeds the chunks, and answers the five evaluation questions from `planning.md`. Because chunking controls *retrieval*, the metrics are retrieval-level and LLM-free:

- **hit@5** — fraction of questions where a top-5 chunk came from a source file known to contain the answer.
- **MRR** — mean reciprocal rank of the first correct-source chunk (rewards putting the right chunk higher).
- **avg_sim** — mean cosine similarity of retrieved chunks to the query (how confident retrieval is).

## Results

| Strategy | Target/Overlap | Chunks | Avg chars | hit@5 | MRR | avg_sim |
|----------|----------------|--------|-----------|-------|-----|---------|
| baseline_600_100 | 600/100 | 66 | 591 | 100% | 0.900 | 0.685 |
| small_300_50 | 300/50 | 119 | 328 | 100% | 1.000 | 0.660 |
| large_1000_150 | 1000/150 | 42 | 904 | 100% | 1.000 | 0.644 |

**Winner: `small_300_50`** — highest hit@5, with MRR and avg_sim as tie-breakers.

## Why

Smaller chunks (300 chars) produce more, tighter segments: each embedding represents a narrower idea, so similarity to a focused question is sharper and the right review is more likely to surface — but a single review's details (food + price + wait) can split across chunks, occasionally hurting recall. Larger chunks (1000 chars) capture whole discussions and rarely split a review, but mixing several restaurants into one embedding dilutes its relevance signal, lowering similarity and sometimes burying the on-topic chunk. The 600-char sentence-aware baseline sits between these: large enough to keep a typical short review intact, small enough to stay topically focused. The numbers above show which trade-off won on this review-heavy corpus.

## Per-question retrieval (hit = correct source in top 5)

### baseline_600_100

- ✅ What do reviewers say about the wait time at Mike's Pastry in the North End? — rank 1
- ✅ Which neighborhood do reviewers recommend for the best ramen in Boston? — rank 1
- ✅ According to reviews, is Neptune Oyster worth the price for its lobster roll? — rank 1
- ✅ What do reviewers recommend for budget-friendly eats in Chinatown? — rank 2
- ✅ Do reviews recommend any good vegetarian or vegan restaurants in Cambridge? — rank 1

### small_300_50

- ✅ What do reviewers say about the wait time at Mike's Pastry in the North End? — rank 1
- ✅ Which neighborhood do reviewers recommend for the best ramen in Boston? — rank 1
- ✅ According to reviews, is Neptune Oyster worth the price for its lobster roll? — rank 1
- ✅ What do reviewers recommend for budget-friendly eats in Chinatown? — rank 1
- ✅ Do reviews recommend any good vegetarian or vegan restaurants in Cambridge? — rank 1

### large_1000_150

- ✅ What do reviewers say about the wait time at Mike's Pastry in the North End? — rank 1
- ✅ Which neighborhood do reviewers recommend for the best ramen in Boston? — rank 1
- ✅ According to reviews, is Neptune Oyster worth the price for its lobster roll? — rank 1
- ✅ What do reviewers recommend for budget-friendly eats in Chinatown? — rank 1
- ✅ Do reviews recommend any good vegetarian or vegan restaurants in Cambridge? — rank 1
