# RAG Setup Instructions – Viral Tech Video System

These steps turn the viral tech video report + charts into a local RAG source your MCP server and Claude can use.

## 1. File placement

In your project repo (under the Ollama MCP server root), create:

- `rag_sources/viral_tech_video_charts_summary.md`
- `rag_sources/viral_tech_video_chunks_charts.md`

Copy the following files into place:

1. The long-form report you already have:
   - `viral_tech_video_system_BADGR_2026.md` → `rag_sources/viral_tech_video_system_BADGR_2026.md`
2. The chart summaries (below):
   - `viral_tech_video_charts_summary.md` (high-level explanation of the two charts).
3. The chunk definitions:
   - `viral_tech_video_chunks_charts.md` (pre-chunked text with tags for platform distribution and format mix).

Your `rag_sources` directory should look like:

- `rag_sources/viral_tech_video_system_BADGR_2026.md`
- `rag_sources/viral_tech_video_charts_summary.md`
- `rag_sources/viral_tech_video_chunks_charts.md`

## 2. Indexing (one-time or on change)

Use a simple indexing script (Python or Node) that:

1. Reads all `rag_sources/*.md` files.
2. Splits documents into chunks:
   - For `viral_tech_video_system_BADGR_2026.md`, use headings/sections as chunk boundaries.
   - For `viral_tech_video_chunks_charts.md`, treat each "Chunk:" block as one chunk.
3. For each chunk:
   - Extract `Text` and `Tags` (for the charts chunks) or use the full section text (for the main report).
   - Generate an embedding vector using your chosen local embedding model.
   - Store `{ id, text, tags, vector }` in a local index file, e.g. `rag_index_viral_videos.json`.

## 3. MCP tool wiring (ollama_rag_query)

Update or implement the `ollama_rag_query` tool handler in your MCP server so that it:

1. Loads `rag_index_viral_videos.json` into memory on first use.
2. Embeds the incoming `query` string using the same embedding model used for indexing.
3. Computes similarity between the query vector and all chunk vectors.
4. Returns the top-k chunk texts (and optionally tags) as the tool result.

This matches the `ollama_rag_query` schema already defined in `social-profile-tools.json`.

## 4. badgr_pipeline integration

In your `badgr_pipeline` implementation:

1. Update classification logic to set `requires_rag = true` when the user mentions:
   - "use the viral tech video system"
   - "use our video patterns"
   - "use my video system docs"
   or when the task explicitly needs strategy grounded in your viral patterns.
2. In `badgr_execute`, when `classification.requires_rag === true`:
   - Call `ollama_rag_query` with a query that combines the platform and high-level request, e.g.:
     - `"viral tech video system context for: " + user_request`
   - Take the retrieved chunks and concatenate their `text` into a `context` string.
   - Pass this `context` into your generation call (e.g., as part of the system prompt for `ollama_generate`).
3. Keep `requires_rag` false for simple bio tweaks or non-strategic tasks to keep things fast and cheap.

## 5. How Claude should use this RAG

In your CLAUDE.md or per-project instructions, tell Claude:

- For any request that asks for strategy grounded in the viral tech video system, first classify the request.
- If `requires_rag` is true, rely on `badgr_execute` to pull in the right context via `ollama_rag_query`.
- Do not manually reload or paste the full viral report; let the RAG index surface relevant chunks.

This makes the viral tech video report and charts part of a reusable, local knowledge base that your MCP server can call whenever a social or video task needs deeper strategy context.
