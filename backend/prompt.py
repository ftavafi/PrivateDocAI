from pathlib import Path

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "legal_extraction.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()


def build_messages(document_text: str) -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this legal document:\n\n{document_text}"},
    ]
