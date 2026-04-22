// src/rag.ts
// Local RAG module for the BADGR viral-tech-video knowledge base.
// Two public operations:
//   buildIndex(ollama) — chunk rag_sources/*.md, embed, write rag_index_viral_videos.json
//   queryRag(ollama, query, topK, filters) — embed query, cosine search, return top-k chunks

import { Ollama } from "ollama";
import {
  readFileSync, writeFileSync, existsSync, readdirSync,
} from "node:fs";
import { join, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __filename     = fileURLToPath(import.meta.url);
const __dirname      = dirname(__filename);
const PROJECT_ROOT   = join(__dirname, "..");

export const RAG_SOURCES_DIR = join(PROJECT_ROOT, "rag_sources");
export const INDEX_PATH      = join(PROJECT_ROOT, "rag_index_viral_videos.json");
export const EMBED_MODEL     = process.env.OLLAMA_EMBED_MODEL ?? "nomic-embed-text";

// rag_setup_instructions_viral_videos.md is meta — not knowledge to be indexed
const SKIP_FILES = new Set(["rag_setup_instructions_viral_videos.md"]);

// ── Types ──────────────────────────────────────────────────────────────────────

export interface RagChunk {
  id:     string;
  source: string;
  text:   string;
  tags:   string[];
  vector: number[];
}

interface RagIndex {
  built_at:    string;
  embed_model: string;
  chunks:      RagChunk[];
}

export interface RagResult {
  id:     string;
  source: string;
  text:   string;
  tags:   string[];
  score:  number;
}


// ── Chunking ───────────────────────────────────────────────────────────────────

// Split general markdown files into sections at ## headings
function chunkByHeadings(text: string, source: string): Array<{ text: string; tags: string[] }> {
  const parts  = text.split(/^## /m);
  const chunks: Array<{ text: string; tags: string[] }> = [];

  for (const part of parts) {
    const trimmed = part.trim();
    if (trimmed.length < 50) continue;
    const heading = trimmed.split("\n")[0].trim();
    chunks.push({
      text: `## ${trimmed}`,
      tags: [source, heading.toLowerCase().replace(/\W+/g, "_").slice(0, 48)],
    });
  }
  return chunks;
}

// Parse "## Chunk: <id>" blocks separated by --- in viral_tech_video_chunks_charts.md
function chunkByChunkBlocks(text: string): Array<{ text: string; tags: string[] }> {
  const blocks  = text.split(/\n---\n/).filter(b => b.includes("**Text:**"));
  const results: Array<{ text: string; tags: string[] }> = [];

  for (const block of blocks) {
    const idMatch   = block.match(/##\s+Chunk:\s*(\S+)/);
    const tagsMatch = block.match(/\*\*Tags:\*\*\s*([^\n]+)/);
    const textMatch = block.match(/\*\*Text:\*\*\s*([\s\S]+)/);
    if (!idMatch || !textMatch) continue;

    const id       = idMatch[1];
    const tags     = tagsMatch
      ? tagsMatch[1].split(",").map(t => t.trim()).filter(Boolean)
      : [id];
    const bodyText = textMatch[1].trim();

    results.push({ text: `[chunk:${id}] ${bodyText}`, tags });
  }
  return results;
}


// ── Math ───────────────────────────────────────────────────────────────────────

function cosineSim(a: number[], b: number[]): number {
  if (a.length === 0 || b.length === 0) return 0;
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na  += a[i] * a[i];
    nb  += b[i] * b[i];
  }
  return na === 0 || nb === 0 ? 0 : dot / (Math.sqrt(na) * Math.sqrt(nb));
}


// ── Index build ────────────────────────────────────────────────────────────────

export async function buildIndex(
  ollama: Ollama,
): Promise<{ chunks_indexed: number; embed_model: string; index_path: string }> {
  const files = readdirSync(RAG_SOURCES_DIR)
    .filter(f => f.endsWith(".md") && !SKIP_FILES.has(f))
    .sort();

  if (files.length === 0) {
    throw new Error(`No indexable .md files found in ${RAG_SOURCES_DIR}`);
  }

  const raw: Array<{ text: string; tags: string[]; source: string }> = [];

  for (const file of files) {
    const content = readFileSync(join(RAG_SOURCES_DIR, file), "utf8");
    const source  = basename(file, ".md");

    if (file === "viral_tech_video_chunks_charts.md") {
      // Pre-chunked file: parse Chunk blocks directly
      for (const c of chunkByChunkBlocks(content)) {
        raw.push({ ...c, source });
      }
    } else {
      // General markdown: split by ## headings
      for (const c of chunkByHeadings(content, source)) {
        raw.push({ ...c, source });
      }
    }
  }

  const chunks: RagChunk[] = [];
  for (let i = 0; i < raw.length; i++) {
    const rc  = raw[i];
    const res = await ollama.embed({ model: EMBED_MODEL, input: rc.text });
    const vec: number[] = Array.isArray(res.embeddings?.[0])
      ? (res.embeddings[0] as number[])
      : [];
    chunks.push({
      id:     `chunk_${i}`,
      source: rc.source,
      text:   rc.text,
      tags:   rc.tags,
      vector: vec,
    });
  }

  const index: RagIndex = {
    built_at:    new Date().toISOString(),
    embed_model: EMBED_MODEL,
    chunks,
  };

  writeFileSync(INDEX_PATH, JSON.stringify(index), "utf8");
  invalidateCache();

  return { chunks_indexed: chunks.length, embed_model: EMBED_MODEL, index_path: INDEX_PATH };
}


// ── Query ──────────────────────────────────────────────────────────────────────

let _cache: RagIndex | null = null;
function invalidateCache(): void { _cache = null; }

function loadIndex(): RagIndex | null {
  if (_cache) return _cache;
  if (!existsSync(INDEX_PATH)) return null;
  try {
    _cache = JSON.parse(readFileSync(INDEX_PATH, "utf8")) as RagIndex;
    return _cache;
  } catch {
    return null;
  }
}

export function indexExists(): boolean {
  return existsSync(INDEX_PATH);
}

export async function queryRag(
  ollama:  Ollama,
  query:   string,
  topK    = 5,
  filters: Record<string, string> = {},
): Promise<RagResult[]> {
  const index = loadIndex();
  if (!index) return [];

  const res  = await ollama.embed({ model: index.embed_model, input: query });
  const qvec: number[] = Array.isArray(res.embeddings?.[0])
    ? (res.embeddings[0] as number[])
    : [];
  if (qvec.length === 0) return [];

  let candidates = index.chunks;

  if (filters["tags"]) {
    const tagSet = new Set(filters["tags"].split(",").map(t => t.trim()));
    candidates = candidates.filter(c => c.tags.some(t => tagSet.has(t)));
  }

  return candidates
    .map(c => ({
      id:    c.id,
      source: c.source,
      text:  c.text,
      tags:  c.tags,
      score: cosineSim(qvec, c.vector),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}
