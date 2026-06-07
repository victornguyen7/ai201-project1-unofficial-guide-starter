"""
Ingestion and chunking for The Unofficial Guide — Boston food & restaurant reviews.

Implements Milestone 3 from planning.md:
  - Load documents from the documents/ folder (.txt, .md, .html)
  - Clean them (strip HTML, normalize whitespace, drop noise)
  - Split into chunks: target 600 chars, extend to the next sentence
    boundary up to a hard max of ~750 chars, with 100-char overlap
  - Keep source name + path as metadata on every chunk

Output: chunks.jsonl in the project root, one JSON object per chunk:
  {"id", "source", "path", "chunk_index", "text", "char_len"}

Usage:
  python src/ingest.py
  python src/ingest.py --docs documents --out chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path

# --- Chunking parameters (from planning.md "Chunking Strategy") ---
TARGET_SIZE = 600   # target chunk size in characters
MAX_SIZE = 750      # hard maximum; cut here if no sentence boundary is found
OVERLAP = 100       # characters of overlap between consecutive chunks

SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".htm"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
class _HTMLTextExtractor(HTMLParser):
    """Collect visible text from HTML, skipping script/style content."""

    _SKIP = {"script", "style", "head", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    return parser.get_text()


def load_documents(docs_dir: Path) -> list[tuple[str, Path, str]]:
    """Return a list of (source_name, path, raw_text) for supported files."""
    docs: list[tuple[str, Path, str]] = []
    for path in sorted(docs_dir.rglob("*")):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() in {".html", ".htm"}:
            raw = strip_html(raw)
        docs.append((path.stem, path, raw))
    return docs


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
# Remove emoji and other symbol/pictographic ranges.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF]",
    flags=re.UNICODE,
)
_WS_RE = re.compile(r"[ \t ]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalize review text: drop URLs/emoji, collapse whitespace."""
    text = _URL_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)
    # Normalize unicode quotes/dashes to plain ASCII for consistent splitting.
    text = (
        text.replace("’", "'").replace("‘", "'")
        .replace("“", '"').replace("”", '"')
        .replace("—", "-").replace("–", "-")
    )
    # Collapse runs of spaces/tabs, trim each line, limit blank-line runs.
    lines = [_WS_RE.sub(" ", ln).strip() for ln in text.splitlines()]
    text = "\n".join(lines)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
# Sentence boundary: ., !, or ? followed by whitespace. Also treat a blank
# line (paragraph break) as a valid boundary.
_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")


def _next_boundary(text: str, start: int, target: int, max_size: int) -> int:
    """
    Choose the end index for a chunk beginning at `start`.

    Target `target` chars; if a sentence boundary exists between
    `target` and `max_size`, end there; otherwise cut at `max_size` (or the
    end of the text). Returns an absolute index into `text`.
    """
    n = len(text)
    if start + target >= n:
        return n

    window_start = start + target
    window_end = min(start + max_size, n)
    window = text[window_start:window_end]

    # Prefer the first sentence end inside the [target, max] window.
    m = _SENTENCE_END_RE.search(window)
    if m:
        return window_start + m.end()

    # Fall back to a paragraph break, then a space, to avoid mid-word cuts.
    para = window.find("\n")
    if para != -1:
        return window_start + para + 1
    space = window.rfind(" ")
    if space != -1:
        return window_start + space + 1

    return window_end


def chunk_text(
    text: str,
    target: int = TARGET_SIZE,
    max_size: int = MAX_SIZE,
    overlap: int = OVERLAP,
) -> list[str]:
    """Split cleaned text into overlapping chunks.

    Defaults match the planning spec (600 target / 750 max / 100 overlap).
    Pass different values to compare alternative chunking strategies.
    """
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = _next_boundary(text, start, target, max_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        # Advance with overlap, but always move forward to avoid looping.
        next_start = end - overlap
        start = next_start if next_start > start else end
    return chunks


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dataclass
class Chunk:
    id: str
    source: str
    path: str
    chunk_index: int
    text: str
    char_len: int


def build_chunks(
    docs_dir: Path,
    target: int = TARGET_SIZE,
    max_size: int = MAX_SIZE,
    overlap: int = OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for source, path, raw in load_documents(docs_dir):
        cleaned = clean_text(raw)
        for i, piece in enumerate(chunk_text(cleaned, target, max_size, overlap)):
            chunks.append(
                Chunk(
                    id=f"{source}-{i}",
                    source=source,
                    path=str(path),
                    chunk_index=i,
                    text=piece,
                    char_len=len(piece),
                )
            )
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest and chunk documents.")
    parser.add_argument("--docs", default="documents", help="documents folder")
    parser.add_argument("--out", default="chunks.jsonl", help="output JSONL file")
    args = parser.parse_args()

    docs_dir = Path(args.docs)
    if not docs_dir.exists():
        raise SystemExit(f"Documents folder not found: {docs_dir.resolve()}")

    chunks = build_chunks(docs_dir)

    out_path = Path(args.out)
    with out_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    # --- Summary stats (useful for the README "Final chunk count") ---
    n_docs = len({c.source for c in chunks})
    if chunks:
        lengths = [c.char_len for c in chunks]
        avg = sum(lengths) / len(lengths)
        print(f"Documents processed : {n_docs}")
        print(f"Chunks created      : {len(chunks)}")
        print(f"Chunk size (chars)  : min {min(lengths)}, avg {avg:.0f}, max {max(lengths)}")
        print(f"Written to          : {out_path.resolve()}")
    else:
        print("No chunks created. Add .txt/.md/.html files to the documents/ folder.")


if __name__ == "__main__":
    main()
