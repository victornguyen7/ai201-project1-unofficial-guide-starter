# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

Food and restaurant reviews in the Boston area. This domain provides valuable knowledge for both Boston residents and tourists looking for a good place to eat in the Boston area. It is also hard to find through official channels, since the most useful opinions are scattered across community forums, local blogs, and user reviews rather than collected in one official source.

---

## Document Sources

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | r/boston | Subreddit threads asking for and sharing restaurant recommendations | https://www.reddit.com/r/boston/ |
| 2 | r/bostonfood | Subreddit focused specifically on Boston-area food and dining | https://www.reddit.com/r/bostonfood/ |
| 3 | Eater Boston | Editorial restaurant guides, reviews, and "best of" lists | https://boston.eater.com/ |
| 4 | The Food Lens | Curated Boston dining guides by category and neighborhood | https://thefoodlens.com/boston/ |
| 5 | Pop.Bop.Shop | Personal blog with 700+ Boston restaurant reviews | https://www.popbopshop.com/ |
| 6 | Confessions of a Chocoholic | Boston-based blog with ongoing restaurant reviews | https://www.confessionsofachocoholic.com/ |
| 7 | Boston Food Truck Blog | Reviews of food trucks across Boston | https://bostonfoodtruckblog.com/ |
| 8 | Boston Magazine — Dining | Magazine restaurant reviews and dining features | https://www.bostonmagazine.com/restaurants/ |
| 9 | Boston.com — Food | Local news outlet food coverage and openings/closings | https://www.boston.com/food/ |
| 10 | Yelp — Boston restaurants | User review text for individual Boston restaurants | https://www.yelp.com/search?find_loc=Boston%2C+MA |

---

## Chunking Strategy

**Chunk size:** 600 characters

**Overlap:** 100 characters 

**Why these choices fit your documents:** Most food reviews are short, so a target chunk size of 600 characters will capture most of a review, often one or two complete reviews including the key details (food, price, service, wait time). To avoid cutting sentences mid-word, the splitter targets 600 characters but extends to the next sentence boundary, up to a hard maximum of about 750 characters; if no boundary is found by then, it cuts at the limit. Reviews longer than this are split into separate chunks while still keeping each chunk's meaning. An overlap of 100 characters ensures a sentence that falls on a chunk boundary still appears intact in an adjacent chunk, making it easier to find and compare chunks.
**Final chunk count:** 66 chunks across the 15 documents, averaging ~591 characters each.

---

## Embedding Model

**Model used:** all-MiniLM-L6-v2 via sentence-transformers.

**Production tradeoff reflection:** To deploy for real users, I would prefer a model with multilingual support, so that a tourist who does not understand English could ask and get suggestions in their native language. I would also prefer a model with higher accuracy on domain-specific text, such as restaurant slang, dish names, and sentiment in reviews. The tradeoff is that a larger, more capable model usually comes with higher latency and cost per query, which I would accept for the better accuracy and language coverage.

---

## Grounded Generation

**System prompt grounding instruction:** Generation uses Groq's `llama-3.3-70b-versatile` with the prompt:

> "You are a Boston food and restaurant guide. You answer questions using ONLY the review excerpts provided in the context below. Rules you MUST follow: Use only information in the provided context. Do not use any outside knowledge. If the context does not contain enough information to answer, say: 'The available reviews don't cover that.' Do not guess or invent details. These are subjective reviews. When sources disagree, say so and summarize the different opinions rather than presenting one as fact. Attribute claims to the sources they came from using the [source] labels given in the context."

**How source attribution is surfaced in the response:** Two ways. Inline, the model cites the bracketed `[source]` labels next to the claims they support. Then `format_output()` appends a deduplicated **Sources:** list at the end, each entry showing the source name and its file path, preserving retrieval order. This lets a reader trace any claim back to the specific review file it came from.

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

**Root cause (tied to a specific pipeline stage):** This is a generation failure. The shop names are present and abundant: of the ramen-related chunks, those from `reddit_bostonfood_ramen`, `bostonfoodtruckblog_allston`, `thefoodlens_allston_cambridge_eats`, and `bostonmagazine_best_restaurants_roundup` repeatedly contain "Yume Wo Katare," "Ganko," and "Ittetsu", and all four of those sources appear in the system's cited sources for Q2, so the names were almost certainly inside the retrieved context window. The model nonetheless answered the question hyper-literally: the prompt asked "which *neighborhood*," and the grounded system prompt instructs it to "keep the answer concise and practical," so it returned only the neighborhood-level claim and dropped the specific-restaurant details that were available in context. In other words, retrieval surfaced the right chunks but generation under-extracted from them.

**What you would change to fix it:** Adjust generation function. Add an instruction to the system prompt to include specific named entities (restaurant/dish names) from the context whenever they support the answer, instead of summarizing to the level the question literally asks for.

---

## Spec Reflection

**One way the spec helped you during implementation:** Writing the Chunking Strategy and Retrieval Approach sections in `planning.md` before coding gave me a detailed plan with all the date, 600-char target, 750 hard max, 100 overlap, sentence-aware boundaries, MiniLM, top-k = 5, that I could hand directly to the AI tool as the spec for each function.

**One way your implementation diverged from the spec, and why:** The spec committed to 600/100 as the production chunking, but my stretch extra comparison tested 300/50 and 1000/150 as well and found that 300/50 chunking actually scored highest on the retrieval metrics. Despite that result, the 600-char chunks keep a typical short review intact in one piece, which makes the generated answers more coherent and the source attribution cleaner than 300-char fragments would. So the divergence is a deliberate choice to weigh end-to-end answer quality over a narrow retrieval score.

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
