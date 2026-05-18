import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

from backend.parser import extract_text
from backend.prompt import build_messages
from backend.validator import extract_json
from backend.chunker import chunk_text, merge_results, estimate_tokens, MAX_TOKENS

app = FastAPI(title="PrivateDoc AI", version="0.5.0")

client = OpenAI(
    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
    api_key="ollama",
)

MODEL = os.getenv("MODEL", "gemma3:12b")

RETRY_SUFFIX = (
    "\n\nYour previous response was not valid JSON. "
    "Return ONLY the raw JSON object with no explanation, "
    "no markdown, no code blocks."
)


class AnalyzeRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    try:
        client.models.list()
        ollama_reachable = True
    except Exception:
        ollama_reachable = False

    return {
        "status": "ok",
        "ollama_reachable": ollama_reachable,
        "model": MODEL,
        "chunk_token_limit": MAX_TOKENS,
    }


def _call_model(messages: list[dict]) -> str:
    """Call Ollama and return the full response text."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.0,
    )
    return response.choices[0].message.content


def _analyze_chunk(chunk: str) -> dict:
    """
    Run one extraction attempt on a single text chunk.
    Retries once with a correction message if the response is not valid JSON.
    """
    messages = build_messages(chunk)

    raw = _call_model(messages)
    try:
        return extract_json(raw)
    except ValueError:
        pass

    messages.append({"role": "assistant", "content": raw})
    messages.append({"role": "user", "content": RETRY_SUFFIX})
    raw = _call_model(messages)
    return extract_json(raw)   # raises ValueError → caller handles it


def _stream_llm(text: str):
    """Generator that streams tokens for the /analyze/stream endpoint."""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=build_messages(text),
        stream=True,
        temperature=0.0,
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token is not None:
            yield token


@app.post("/analyze/text")
def analyze_text(request: AnalyzeRequest):
    """Phase 2 endpoint: raw text in, raw response out. Kept for testing."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": request.text}],
    )
    return {"response": response.choices[0].message.content}


@app.post("/analyze/stream")
async def analyze_stream(file: UploadFile = File(...)):
    """Streams raw tokens — useful for watching the model think during dev."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    pdf_bytes = await file.read()
    text = extract_text(pdf_bytes)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from this PDF.")
    return StreamingResponse(_stream_llm(text), media_type="text/plain")


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Main endpoint. Accepts a PDF, returns structured JSON.
    Automatically chunks documents that exceed the token limit and merges results.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()
    text = extract_text(pdf_bytes)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from this PDF.")

    token_count = estimate_tokens(text)
    chunks = chunk_text(text)

    chunk_results: list[dict] = []
    for i, chunk in enumerate(chunks, 1):
        try:
            chunk_results.append(_analyze_chunk(chunk))
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Chunk {i}/{len(chunks)}: model failed to return valid JSON. Error: {e}",
            )

    result = merge_results(chunk_results)

    return {
        "filename": file.filename,
        "token_estimate": token_count,
        "chunks": len(chunks),
        "result": result,
    }
