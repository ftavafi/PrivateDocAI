import os
import re

# Gemma 3 uses a 256k-vocab SentencePiece tokenizer. tiktoken (OpenAI-specific)
# would give inaccurate counts for it. A character-based approximation is simpler,
# portable across all models, and accurate enough for chunking decisions.
CHARS_PER_TOKEN = 4

# Leave headroom for the system prompt (~300 tokens) and the model's response
# (~1,000 tokens). Default: 60,000 tokens = 240,000 chars per chunk.
MAX_TOKENS = int(os.getenv("CHUNK_TOKENS", "60000"))


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def chunk_text(text: str, max_tokens: int = MAX_TOKENS) -> list[str]:
    """
    Split text into chunks that each fit within max_tokens.
    Splits on paragraph boundaries so sentences are never cut mid-way.
    Returns a list with one element if the document fits in one pass.
    """
    max_chars = max_tokens * CHARS_PER_TOKEN

    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n\n+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 2  # +2 for the \n\n separator
        if current and current_len + para_len > max_chars:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def merge_results(results: list[dict]) -> dict:
    """
    Merge structured JSON outputs from multiple document chunks into one.
    Strategy per field type:
      - Scalar (date, string): first non-null value wins
      - List (parties, obligations, clauses): union with deduplication
      - Summary: chunk summaries joined in order
    """
    if len(results) == 1:
        return results[0]

    def first_non_null(key: str):
        return next((r[key] for r in results if r.get(key) is not None), None)

    def union_lists(key: str) -> list[str]:
        seen: set[str] = set()
        combined: list[str] = []
        for r in results:
            for item in r.get(key) or []:
                if item and item != "None identified" and item not in seen:
                    seen.add(item)
                    combined.append(item)
        return combined if combined else ["None identified"]

    summaries = [r["summary"] for r in results if r.get("summary")]

    return {
        "parties":              union_lists("parties"),
        "effective_date":       first_non_null("effective_date"),
        "termination_date":     first_non_null("termination_date"),
        "payment_terms":        first_non_null("payment_terms"),
        "key_obligations":      union_lists("key_obligations"),
        "risky_clauses":        union_lists("risky_clauses"),
        "governing_law":        first_non_null("governing_law"),
        "summary":              " ".join(summaries),
        "follow_up_questions":  union_lists("follow_up_questions"),
    }
