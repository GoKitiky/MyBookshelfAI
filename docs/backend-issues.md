# Backend — deferred & follow-ups

Issues and ideas for API, enrichment, and LLM pipelines.

## Enrichment & reader text

### Personal review: separate processing from book metadata

**Context:** `_build_enrichment_prompt` in `app/services/llm.py` used to append the reader’s `book.review` (truncated) as “Reader’s personal review” inside the same prompt that asks the model to search the web and extract canonical-style JSON (genres, themes, mood, complexity, plot summary, similar authors). That coupling mixed **subjective reader signal** with **book-in-the-world** enrichment.

**Current behavior:** The review block was removed from the enrichment prompt so enrichment is driven by title, author, and web search only.

**Follow-up (not implemented):**

- **Dedicated LLM step for reader text** — run a separate, small prompt (or structured output) over `review` and/or `notes_md` to produce **personal reader tags** (or a short structured “reader reaction” object), instead of stuffing raw review text into the main enrichment call.
- **Wire `notes_md`** — pipeline `Book` loading (`app/routers/recommend.py` → `Book(...)`) does not pass `notes_md` from the DB today; any personal-text feature should decide which fields feed the reader step and keep cache keys in sync when that text changes (`EnrichmentService` cache is keyed by title + author only).
- **Profile / recommendations** — clarify whether personal tags merge into `EnrichedBook`, sit beside it, or feed only the reader profile and scoring layer.

**Rationale:** Keeps enrichment cache stable and semantically clear, while still allowing personalized signals where they belong.
