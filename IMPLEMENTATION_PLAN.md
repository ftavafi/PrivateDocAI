# PrivateDoc AI — Implementation Plan

## Project Summary

An offline-first legal document review assistant. Users upload contracts, NDAs, and
leases. A local LLM extracts structured data (parties, dates, obligations, risky clauses).
Sensitive files never leave the user's machine.

---

## Technology Stack

### Why Each Tool Was Chosen

| Layer | Tool | Why |
|---|---|---|
| Model runtime | **Ollama** | Downloads models, handles quantization, exposes a local API on `localhost:11434` that is compatible with the OpenAI Python SDK — so the app code barely changes if you swap models |
| LLM model | **Gemma 3 12B (Q4_K_M)** | Designed explicitly for on-device deployment; runs well on Apple Silicon; 4-bit quantized variant fits in ~8 GB RAM with acceptable quality |
| Backend | **FastAPI** | Lightweight, async Python framework; first-class support for `StreamingResponse` which is essential for token-by-token streaming |
| PDF parsing | **pdfplumber** | Pure Python, no external services, reliable text extraction with layout awareness |
| Frontend | **Streamlit** | Python-only; avoids React/CSS complexity for the MVP; has native `st.write_stream` for streaming output |
| Language | **Python 3.11+** | Entire stack is Python — no context switching between languages |

### What Quantization Means (Practically)

- Full precision (float32): ~32 GB, too slow for interactive use on a laptop
- 4-bit quantized (Q4_K_M): ~5 GB, fast enough for interactive use, minor quality loss
- Ollama selects quantization via model tag: `gemma3:12b`

### The OpenAI-Compatibility Trick

Ollama exposes `POST http://localhost:11434/v1/chat/completions`.
The OpenAI Python SDK accepts a custom `base_url` and a dummy `api_key`.
Result: the same Python code works against Ollama locally and OpenAI in the cloud —
you just change one environment variable.

---

## Architecture Diagram

```
User (Browser)
    │
    │  HTTP (upload + stream)
    ▼
┌──────────────────────────────────┐
│  Streamlit  (frontend)           │
│  - file upload widget            │
│  - st.write_stream for output    │
└──────────────┬───────────────────┘
               │ HTTP POST /analyze
               ▼
┌──────────────────────────────────┐
│  FastAPI  (backend)              │
│  - receives PDF                  │
│  - extracts text (pdfplumber)    │
│  - chunks if too long            │
│  - builds prompt                 │
│  - calls Ollama                  │
│  - streams response back         │
└──────────────┬───────────────────┘
               │ localhost:11434
               ▼
┌──────────────────────────────────┐
│  Ollama  (model server)          │
│  - gemma3:12b     │
│  - runs entirely on local CPU/GPU│
└──────────────────────────────────┘
```

---

## Build Phases

Each phase has a single goal and a concrete definition of done.
**Do not move to the next phase until the current one works.**

---

### Phase 1 — Local Model Works (No App)

**Goal:** Verify Ollama is installed and a model responds to a prompt.

**Steps:**
1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull the model: `ollama pull gemma3:12b`
3. Run a prompt from the terminal: `ollama run gemma3:12b "Summarize this in one sentence: An NDA is a contract..."`
4. Observe the response

**Done when:** You get a coherent response in the terminal.

**What you learn:** How Ollama works as a model server, what quantization tags look like,
how fast the model is on your hardware.

---

### Phase 2 — Backend Skeleton (No Frontend, No PDF)

**Goal:** A FastAPI endpoint that accepts a text string, calls Ollama, returns a response.

**Steps:**
1. Create a Python virtual environment
2. Install: `fastapi`, `uvicorn`, `openai` (for the Ollama-compatible client)
3. Create `main.py` with one POST endpoint `/analyze` that accepts `{"text": "..."}`
4. Inside the endpoint, call Ollama via the OpenAI SDK with `base_url="http://localhost:11434/v1"`
5. Return the raw LLM response as JSON
6. Test with `curl` or the FastAPI `/docs` interactive UI

**Done when:** `curl -X POST http://localhost:8000/analyze -d '{"text":"What is an NDA?"}'`
returns a JSON response from the local model.

**What you learn:** How FastAPI works, how the OpenAI SDK connects to Ollama,
the request/response cycle.

---

### Phase 3 — PDF Parsing Works

**Goal:** Extract clean text from a real legal PDF.

**Steps:**
1. Install `pdfplumber`
2. Write a standalone script `parse_pdf.py` that opens a PDF and prints the extracted text
3. Test on at least two PDFs: a short NDA and a longer contract
4. Identify problems: garbled text, headers/footers, page numbers polluting the output
5. Add basic cleanup: strip page numbers, collapse whitespace
6. Wire the parser into the FastAPI endpoint — endpoint now accepts a file upload instead of raw text

**Done when:** You can `curl -F "file=@contract.pdf" http://localhost:8000/analyze`
and get a response that clearly processed the PDF content.

**What you learn:** How PDF text extraction works, why it's imperfect,
FastAPI file uploads (`UploadFile`).

---

### Phase 4 — Streaming Works

**Goal:** Tokens appear in the terminal (and later the browser) as they are generated,
not all at once after a 20-second wait.

**Steps:**
1. Modify the Ollama API call to use `stream=True`
2. Change the FastAPI response to `StreamingResponse` with `media_type="text/event-stream"`
3. Yield each token chunk as it arrives from Ollama
4. Test by watching the terminal output with `curl --no-buffer http://localhost:8000/analyze`
5. Observe tokens printing one at a time

**Done when:** You see tokens streaming to the terminal in real time, not a single
delayed dump.

**What you learn:** Server-sent events, async generators in FastAPI,
why streaming matters for perceived performance.

---

### Phase 5 — Structured Extraction via Prompt Engineering

**Goal:** The LLM returns a reliable JSON object with the fields you care about.

**Target output shape:**
```json
{
  "parties": ["Acme Corp", "Jane Doe"],
  "effective_date": "2024-01-15",
  "termination_date": "2026-01-15",
  "payment_terms": "Net 30",
  "key_obligations": ["...", "..."],
  "risky_clauses": ["...", "..."],
  "summary": "...",
  "follow_up_questions": ["...", "..."]
}
```

**Steps:**
1. Write a system prompt that instructs the model to return only valid JSON
2. Include the target JSON schema in the system prompt as an example
3. Test on 3–4 different document types (NDA, lease, employment contract)
4. Identify where the model hallucinates or misses fields
5. Iterate the prompt until output is consistent
6. Add a JSON validation step in FastAPI — if the response is not valid JSON, retry once

**Done when:** 3 out of 4 test documents return valid, populated JSON with no manual intervention.

**What you learn:** Prompt engineering, structured output patterns,
why local models need more explicit instructions than GPT-4.

---

### Phase 6 — Context Window Handling

**Goal:** The app does not break on documents longer than the model's context window (~8K tokens).

**Steps:**
1. Install `tiktoken` (or count characters as a proxy) to estimate token count
2. If the document exceeds a threshold (e.g., 6000 tokens), split it into chunks
3. Analyze each chunk independently, collecting partial results
4. Merge partial results into a single output (combine lists, pick the longest summary)
5. Test on a 20-page contract

**Done when:** A 20-page contract produces a complete structured output without errors.

**What you learn:** Chunking strategies, token counting,
the tradeoff between context size and model quality.

---

### Phase 7 — Streamlit Frontend

**Goal:** A clean browser UI for uploading and viewing results. No raw JSON visible to the user.

**Steps:**
1. Install `streamlit`
2. Create `app.py` with a file uploader widget
3. On upload, call the FastAPI backend via `httpx` or `requests`
4. Use `st.write_stream` to display streaming output token by token
5. Parse the final JSON and display each field in a readable format (tables, expanders)
6. Add a sidebar with "About" text explaining the privacy guarantee

**Done when:** You can upload a PDF in the browser and watch the analysis stream in
in real time, displayed in a readable layout.

**What you learn:** Streamlit basics, connecting a frontend to a backend,
how to present JSON data in a user-friendly way.

---

### Phase 8 — Polish & Portfolio Packaging

**Goal:** The project is presentable to a hiring manager or client.

**Steps:**
1. Write a `README.md` with:
   - The privacy/offline pitch (one paragraph)
   - A screenshot or GIF of the UI
   - Setup instructions (install Ollama, pull model, run backend, run frontend)
   - Architecture diagram
2. Create `requirements.txt`
3. Add a `.env.example` for any configurable values (model name, port)
4. Record a 2-minute demo video
5. Push to GitHub

**Done when:** A stranger can clone the repo, follow the README, and have it running in 10 minutes.

---

## Decision Log

Decisions made upfront so you don't revisit them mid-build:

| Decision | Choice | Alternative Considered | Reason |
|---|---|---|---|
| Frontend framework | Streamlit | React | Avoid frontend complexity in MVP |
| LLM model | Gemma 3 12B | Llama 3, Qwen 3 | Best on-device performance on Apple Silicon |
| Quantization level | Q4_K_M | Q8, full precision | ~5GB footprint, good speed/quality balance |
| Output format | Structured JSON | Markdown, plain text | Easier to render in UI, testable |
| Context overflow strategy | Chunking | RAG | Simpler to implement; RAG is Phase 2 |
| PDF parser | pdfplumber | pypdf, pymupdf | Better layout-aware extraction |

---

## Future Phases (After MVP)

These are explicitly out of scope for now but worth knowing exist:

- **RAG (Retrieval-Augmented Generation):** Embed the document into a local vector store
  (ChromaDB or FAISS), retrieve relevant chunks per question. Better than chunking for
  long documents.
- **Multi-document analysis:** Compare two contracts side by side.
- **Redline detection:** Highlight changed clauses between contract versions.
- **Local embeddings:** Use a local embedding model (e.g., `nomic-embed-text`) instead
  of any cloud embedding API.
- **Electron or Tauri desktop app:** Package the whole thing as a native desktop app
  so there is no server to run.
