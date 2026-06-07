# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

This system answers questions about food and restaurants in the Boston area, drawing on the kind of opinionated, first-hand reviews that real diners write. It covers where to find specific dishes (ramen, lobster rolls, soup dumplings, dim sum), what the experience is actually like (wait times, prices, whether a splurge is "worth it"), and recommendations by neighborhood and dietary need (budget eats in Chinatown, vegetarian/vegan spots in Cambridge).

This knowledge is valuable because the most useful dining opinions are subjective and experiential — they live in community forums, local food blogs, and user-review sites rather than in any official directory. A restaurant's own website will never tell you the line is 30 minutes on a weekend, that the hot-buttered lobster roll is the one to order, or that Allston is the neighborhood for ramen. That signal is scattered across many sources, so it is hard to find and compare through official channels. The system consolidates it and grounds every answer in the underlying reviews.

---

## Document Sources

The corpus is 15 review documents saved in `documents/` (one source file each), spanning Reddit threads, local food blogs, editorial guides, a magazine, a local-news outlet, and Yelp user reviews. Each was cleaned and chunked into the 66 chunks in `chunks.jsonl`.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | r/boston (pizza thread) | Reddit thread | https://www.reddit.com/r/boston/ → `documents/reddit_boston_pizza_thread.txt` |
| 2 | r/boston (North End) | Reddit thread | https://www.reddit.com/r/boston/ → `documents/sample_reddit_northend.txt` |
| 3 | r/bostonfood (ramen) | Reddit thread | https://www.reddit.com/r/bostonfood/ → `documents/reddit_bostonfood_ramen.txt` |
| 4 | Eater Boston — seafood guide | Editorial guide | https://boston.eater.com/ → `documents/eater_boston_seafood_guide.txt` |
| 5 | Eater Boston — South End brunch | Editorial guide | https://boston.eater.com/ → `documents/eater_boston_southend_brunch.txt` |
| 6 | The Food Lens — Allston/Cambridge | Dining guide | https://thefoodlens.com/boston/ → `documents/thefoodlens_allston_cambridge_eats.txt` |
| 7 | The Food Lens — Chinatown budget | Dining guide | https://thefoodlens.com/boston/ → `documents/thefoodlens_chinatown_budget.txt` |
| 8 | Pop.Bop.Shop — Cambridge vegetarian | Personal blog (HTML) | https://www.popbopshop.com/ → `documents/popbopshop_cambridge_vegetarian.html` |
| 9 | Confessions of a Chocoholic — Cambridge | Personal blog | https://www.confessionsofachocoholic.com/ → `documents/confessions_chocoholic_cambridge_dessert.txt` |
| 10 | Boston Food Truck Blog — Allston | Blog | https://bostonfoodtruckblog.com/ → `documents/bostonfoodtruckblog_allston.txt` |
| 11 | Boston Magazine — best restaurants | Magazine roundup | https://www.bostonmagazine.com/restaurants/ → `documents/bostonmagazine_best_restaurants_roundup.txt` |
| 12 | Boston Magazine — North End pastry | Magazine feature | https://www.bostonmagazine.com/restaurants/ → `documents/bostonmagazine_northend_pastry.txt` |
| 13 | Boston.com — Chinatown openings | Local-news food coverage | https://www.boston.com/food/ → `documents/boston_com_chinatown_openings.txt` |
| 14 | Yelp — Neptune Oyster | User reviews | https://www.yelp.com/ → `documents/yelp_neptune_oyster_reviews.txt` |
| 15 | Yelp — Gourmet Dumpling House | User reviews | https://www.yelp.com/ → `documents/yelp_gourmet_dumpling_reviews.txt` |

---

## Chunking Strategy

**Chunk size:** Target 600 characters, sentence-aware. The splitter aims for 600 characters but extends to the next sentence boundary (`.`, `!`, `?`, or a paragraph break), up to a hard maximum of ~750 characters; if no boundary is found by then, it cuts at the limit. (See `TARGET_SIZE`, `MAX_SIZE` in `src/ingest.py`.)

**Overlap:** 100 characters between consecutive chunks.

**Why these choices fit your documents:** The corpus is review-heavy, and most individual reviews are short — a 600-character target captures roughly one to two complete reviews including the details that matter (food, price, service, wait time) without slicing a sentence mid-word. Extending to the next sentence boundary keeps each chunk readable and self-contained, which matters because the embedding represents the whole chunk. The 100-character overlap means a sentence that lands on a boundary still appears intact in the adjacent chunk, reducing the chance that a key detail is lost between two chunks. Preprocessing before chunking (in `src/ingest.py`): HTML files are run through a parser that drops `script`/`style`/`head` and keeps only visible text; then all documents have URLs and emoji removed, smart quotes/dashes normalized to ASCII, and whitespace/blank-line runs collapsed.

**Final chunk count:** 66 chunks across the 15 documents (`chunks.jsonl`), averaging ~591 characters each.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. Embeddings are stored in a persistent ChromaDB collection configured for cosine similarity, and queries retrieve the top-k = 5 chunks (`src/retrieve.py`). I chose MiniLM because it is small, fast, runs locally with no API cost, and is a strong general-purpose sentence embedder — well matched to short review text and to a project where the whole corpus is only 66 chunks.

**Production tradeoff reflection:** If I were deploying this for real users and cost were not a constraint, I would weigh a few tradeoffs against MiniLM. First, multilingual support: a larger multilingual model would let a tourist ask in their native language and still match English reviews, which MiniLM handles poorly. Second, domain accuracy: review text is full of restaurant names, dish names, and slang, and a model fine-tuned on or simply stronger at this kind of informal text (or a larger OpenAI/Cohere embedding) would draw sharper distinctions — e.g., reliably separating two ramen shops. Third, context length: MiniLM truncates at 256 tokens, so a longer chunk is silently cut; a model with a longer context window would let me embed bigger, review-complete chunks without losing the tail. The cost of moving up is higher latency and per-query expense (and, for API models, sending data off-device), which for a real product I would accept in exchange for the accuracy and language coverage.

---

## Grounded Generation

**System prompt grounding instruction:** Generation (`src/generate.py`) uses Groq's `llama-3.3-70b-versatile` at low temperature (0.2) with a system prompt that enforces grounding through explicit rules:

> "You are a Boston food and restaurant guide. You answer questions using ONLY the review excerpts provided in the context below. Rules you MUST follow: Use only information in the provided context. Do not use any outside knowledge. If the context does not contain enough information to answer, say: 'The available reviews don't cover that.' Do not guess or invent details. These are subjective reviews. When sources disagree, say so and summarize the different opinions rather than presenting one as fact. Attribute claims to the sources they came from using the [source] labels given in the context."

Beyond the wording, grounding is enforced structurally. The retrieved chunks are formatted into a labeled context block where each chunk is prefixed with its source name in brackets (`[yelp_neptune_oyster_reviews]`), and the user message hands the model only that block plus the question, instructing it to answer "using only the context above." Because the model never sees the full documents — only the top-5 retrieved chunks — and the temperature is low, it stays close to the source text. The instruction to admit when reviews disagree (rather than pick one) directly addresses the noisy, contradictory nature of subjective reviews.

**How source attribution is surfaced in the response:** Two ways. Inline, the model cites the bracketed `[source]` labels next to the claims they support (e.g., "according to `[bostonmagazine_northend_pastry]`"). Then `format_output()` appends a deduplicated **Sources:** list at the end, each entry showing the source name and its file path, preserving retrieval order. This lets a reader trace any claim back to the specific review file it came from.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What do reviewers say about the wait time at Mike's Pastry in the North End? | Long lines, especially weekends/evenings, but the line moves fast; many suggest going on a weekday or trying Modern Pastry nearby to avoid the wait. | Line is "famously fast-moving"; ~20–30 min on weekends/evenings, "25 minutes tops even when wrapped around"; weekday afternoon is the "cheat code" to walk right in. Sources: bostonmagazine_northend_pastry, sample_reddit_northend. | Relevant | Accurate |
| 2 | Which neighborhood do reviewers recommend for the best ramen in Boston? | Allston is most cited, with spots like Yume Wo Katare (rich tonkotsu, long lines) and Ganko Ittetsu Ramen. | Allston — "ramen central" / "densest cluster of ramen in greater Boston." Names the neighborhood correctly but does not name specific shops (Yume Wo Katare, Ganko Ittetsu). | Relevant | Partially accurate |
| 3 | According to reviews, is Neptune Oyster worth the price for its lobster roll? | Mostly yes — the (hot buttered) lobster roll is praised as among the city's best, though expensive with a long wait since it takes no reservations. | Yes — "worth every penny and every minute of the wait," "best-in-class flavor," worth it for a special meal; notes it's pricey (~$30–35) and crowded, with cheaper alternatives like James Hook. | Relevant | Accurate |
| 4 | What do reviewers recommend for budget-friendly eats in Chinatown? | Dim sum / noodle spots like Gourmet Dumpling House (soup dumplings), Hei La Moon (dim sum), and Beach Street bakeries — cheap and filling. | Gourmet Dumpling House (soup dumplings, scallion pancakes, pork buns), plus pho, noodle/rice plates, and bakery snacks under $15; Chinatown called the city's best value. Names GDH and bakeries but not Hei La Moon. | Relevant | Accurate |
| 5 | Do reviews recommend any good vegetarian or vegan restaurants in Cambridge? | Yes — Veggie Galaxy in Central Square (vegetarian diner w/ vegan options) and Life Alive are commonly recommended. | Yes — Veggie Galaxy (Central Square, vegetarian diner with many vegan options) and Life Alive (healthy bowls/wraps); also mentions Clover in Harvard Square. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** Q2 — "Which neighborhood do reviewers recommend for the best ramen in Boston?"

**What the system returned:** The correct neighborhood (Allston — "ramen central," "densest cluster of ramen in greater Boston") but no specific restaurants. The expected answer also names Yume Wo Katare and Ganko Ittetsu Ramen, which the response omitted entirely.

**Root cause (tied to a specific pipeline stage):** This is a *generation* failure, not a retrieval one. I confirmed against the corpus that the shop names are present and abundant: of the ramen-related chunks, those from `reddit_bostonfood_ramen`, `bostonfoodtruckblog_allston`, `thefoodlens_allston_cambridge_eats`, and `bostonmagazine_best_restaurants_roundup` repeatedly contain "Yume Wo Katare," "Ganko," and "Ittetsu" — and all four of those sources appear in the system's cited sources for Q2, so the names were almost certainly inside the retrieved context window. The model nonetheless answered the question hyper-literally: the prompt asked "which *neighborhood*," and the grounded system prompt instructs it to "keep the answer concise and practical," so it returned only the neighborhood-level claim and dropped the specific-restaurant details that were available in context. In other words, retrieval surfaced the right chunks but generation under-extracted from them.

**What you would change to fix it:** Adjust generation rather than chunking. Add an instruction to the system prompt to include specific named entities (restaurant/dish names) from the context whenever they support the answer, instead of summarizing to the level the question literally asks for. As a verification step I would also re-run Q2 and inspect the actual top-5 chunk *text* (not just source labels) to confirm the names sit within the retrieved spans; if a future query's names turned out to be just outside the top-k, the fix would instead be to raise top-k or de-duplicate near-identical chunks so more distinct content fits in the window.

---

## Spec Reflection

**One way the spec helped you during implementation:** Writing the Chunking Strategy and Retrieval Approach sections in `planning.md` before coding gave me precise numbers — 600-char target, ~750 hard max, 100 overlap, sentence-aware boundaries, MiniLM, top-k = 5 — that I could hand directly to the AI tool as the spec for each function. Because the requirements were concrete rather than "split the text into chunks," the generated `chunk_text()` and `retrieve()` matched what I wanted on the first pass, and I could verify the output against explicit targets (chunk sizes, overlap, relevance of retrieved chunks) instead of guessing whether it was "right."

**One way your implementation diverged from the spec, and why:** The spec committed to 600/100 as the production chunking, but my stretch comparison (`src/compare_chunking.py`, `chunking_comparison.md`) tested 300/50 and 1000/150 as well and found that **small_300_50** actually scored highest on the retrieval metrics (hit@5 100% with MRR 1.000 vs. the baseline's 0.900). Despite that result, I kept the 600/100 baseline as the live index rather than switching to the measured winner. The reason is that the metric is retrieval-only and LLM-free by design, and the margin is small (all three strategies hit 100% on the 5 questions); the 600-char chunks keep a typical short review intact in one piece, which makes the generated answers more coherent and the source attribution cleaner than 300-char fragments would. So the divergence is a deliberate choice to weigh end-to-end answer quality over a narrow retrieval score.

---

## AI Usage

**Instance 1 — Ingestion & chunking (`src/ingest.py`)**

- *What I gave the AI:* My Documents table and Chunking Strategy section from `planning.md`, with the request to write a loader for the `documents/` folder plus a `chunk_text()` function splitting text into 600-character chunks with 100-character overlap, breaking near sentence boundaries.
- *What it produced:* A script that loads `.txt`/`.md`/`.html` files, cleans them, and chunks them, writing `chunks.jsonl` with source metadata per chunk.
- *What I changed or overrode:* I directed it to make chunking *sentence-aware* rather than a fixed character cut — target 600 but extend to the next sentence boundary up to a ~750 hard max — so reviews aren't sliced mid-word. I also had it add HTML stripping (for the Pop.Bop.Shop `.html` file) and noise cleaning (URLs, emoji, smart-quote normalization) before chunking, which weren't in the first version.

**Instance 2 — Embedding & retrieval (`src/retrieve.py`)**

- *What I gave the AI:* My Retrieval Approach section and the architecture diagram, asking it to embed the chunks with all-MiniLM-L6-v2, store them in ChromaDB, and write `retrieve(query, k=5)`.
- *What it produced:* Code that embeds all chunks and a `retrieve()` that returns the top-k chunks with their source, path, and score.
- *What I changed or overrode:* I had it configure the Chroma collection for cosine similarity explicitly (`hnsw:space: cosine`) rather than the default L2, since cosine is the right metric for normalized sentence embeddings. I also added a `build_index()` guard that only re-embeds when the stored chunk count doesn't match `chunks.jsonl`, so the index isn't rebuilt on every run.
