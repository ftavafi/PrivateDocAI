import json
import re


def extract_json(raw: str) -> dict:
    """
    Parse a JSON object from a model response.
    Handles two common failure modes:
      1. Model wraps JSON in a markdown code block (```json ... ```)
      2. Model adds preamble text before the opening brace
    Raises ValueError if no valid JSON object can be found.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Find the first { and last } to isolate the JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response.")

    candidate = cleaned[start : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e}\n\nRaw candidate:\n{candidate}") from e
