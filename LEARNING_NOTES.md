# PrivateDoc AI — Learning Notes

Technical and conceptual explanations for each build phase.
Written for someone with a strong ML/NLP background catching up on modern LLM application patterns.

---

## Phase 1 — Local Model Works

### What Ollama Actually Is

Ollama is not a model. It is a **model server** — a process that runs in the background,
manages model files on disk, loads them into memory on demand, and exposes an HTTP API
so your application code can talk to the model without knowing anything about how
inference works internally.

Think of it like a database server (Postgres, MySQL) but for LLMs:

- The server runs as a background daemon
- Your app connects to it over a local port (11434)
- You send requests, get responses
- You don't manage memory, GPU allocation, or model loading yourself

This is a meaningful abstraction shift from the pre-LLM era. Previously, if you wanted
to run a model locally (e.g., a fine-tuned BERT for NER), you loaded it directly in
Python with `torch.load()` or `transformers.from_pretrained()`. The model lived inside
your process. Ollama externalizes the model into its own process, which means:

- Multiple apps can share one running model
- The model stays warm between requests (no reload cost)
- Your app code is decoupled from the inference runtime

---

### What Quantization Is (At the Weights Level)

You know this from your deep learning background, but the terminology has standardized
around GGUF quantization schemes in the local LLM world. Here is the mapping:

| GGUF tag | Bits per weight | What it means |
| --- | --- | --- |
| `f32` | 32 | Full float32 — original training precision |
| `f16` | 16 | Half precision — minimal quality loss |
| `q8_0` | 8 | 8-bit integer quantization |
| `q4_K_M` | ~4.5 | 4-bit with K-quant, medium balance — **what gemma3:12b uses** |
| `q4_K_S` | ~4.3 | 4-bit with K-quant, small (faster, slightly lower quality) |
| `q2_K` | ~2.6 | Very aggressive — noticeable quality degradation |

The "K" in `q4_K_M` refers to **K-quant**, a more sophisticated 4-bit scheme that
applies different quantization levels to different weight matrices based on their
sensitivity, rather than quantizing everything uniformly. This is why `q4_K_M` gives
noticeably better quality than a naive 4-bit quantization.

**Practical rule:** `q4_K_M` is the community default for interactive use. It gives
~75% size reduction vs. f16 with quality that is usually indistinguishable for
instruction-following tasks.

---

### The GGUF Format

**GGUF** stands for **GGML Unified Format**. It is a single binary file that contains
everything needed to run a model — weights, architecture metadata, and the tokenizer —
with no external dependencies.

#### Where It Came From

Before GGUF, running a model locally meant:

- Download weights as PyTorch `.bin` or HuggingFace `.safetensors`
- Install the correct version of PyTorch, Transformers, CUDA, etc.
- Write Python inference code that knows the model's architecture
- Handle the tokenizer separately via its own config files

This worked fine when you were loading a fine-tuned BERT into your own process. It
breaks down when you want to ship a model to a non-developer's machine.

**Georgi Gerganov** (who also wrote whisper.cpp) created GGML — a pure C tensor
library — and GGUF as its self-contained model format. One file, runs anywhere,
no Python required.

#### What a GGUF File Contains

```text
model.gguf
├── Header
│   ├── Architecture metadata  (n_layers, n_heads, hidden_dim, vocab_size...)
│   └── Hyperparameters        (rope_freq, attention_type, activation function...)
├── Tokenizer
│   ├── Vocabulary             (all tokens as strings)
│   ├── Token scores / merges  (BPE merge rules)
│   └── Special tokens         (BOS, EOS, PAD token IDs)
└── Tensors
    ├── Stored in memory-mappable layout
    └── Each tensor quantized to the specified bit width
```

No separate `tokenizer.json`. No separate `config.json`. No framework version to match.
One file, fully self-describing.

#### Why the Layout Matters for Inference Speed

GGUF tensors are stored in **memory-mapped layout** — the file is mapped directly into
virtual address space. When Ollama loads a model, the OS pages in only the weights
needed during each forward pass rather than copying the entire file into RAM upfront.

On Apple Silicon this is especially efficient because the CPU and GPU share unified
memory — weights are loaded once and used by both compute units without copying.
This is why an 8GB model "loads" in ~3 seconds rather than the ~30 seconds you would
expect from a sequential 8GB disk read.

#### GGUF vs. safetensors (the HuggingFace format)

| Property | GGUF | safetensors |
| --- | --- | --- |
| Self-contained (includes tokenizer) | Yes | No |
| Quantization support | Built-in | No |
| Runtime dependency | llama.cpp / Ollama | PyTorch / Transformers |
| Best for | Local inference, edge devices | Training, fine-tuning, cloud serving |

#### The Ecosystem

GGUF is now the standard format for local inference:

| Tool | Uses GGUF |
| --- | --- |
| **Ollama** | Yes — wraps llama.cpp internally |
| **llama.cpp** | Yes — the original runtime GGUF was built for |
| **LM Studio** | Yes |
| **Jan.ai** | Yes |
| **HuggingFace Hub** | Hosts GGUF files alongside `.safetensors` |

**Interview note:** "GGUF + llama.cpp (or Ollama)" is the standard answer to "how do
you run LLMs locally on a laptop." vLLM is the GPU-cluster equivalent for server-side
inference but uses different formats. For edge/desktop deployment, GGUF is the standard.

#### GGUF is the Container — Quantization is the Compression

These are two separate concerns that appear together in filenames:

```text
gemma-3-12b-instruct-q4_K_M.gguf
│             │        │
│             │        └── Quantization scheme (4-bit K-quant medium)
│             └─────────── Model size (12 billion parameters)
└───────────────────────── Model family and variant
```

When Ollama pulls `gemma3:12b` it downloads a GGUF file quantized to Q4_K_M.
The format (GGUF) and the compression (Q4_K_M) are independent decisions
that happen to be bundled in the same file.

---

### The OpenAI-Compatible API — Why This Matters

When OpenAI released the Chat Completions API (`/v1/chat/completions`), it became the
de facto standard interface for LLMs. The request shape:

```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Summarize this contract."}
  ],
  "stream": true
}
```

Ollama exposes **the exact same endpoint shape** at `localhost:11434/v1/chat/completions`.
The only difference is the `model` field uses your local model name.

This means the OpenAI Python SDK — which is just an HTTP client with a typed interface —
works against Ollama with one change:

```python
# Talking to OpenAI
client = OpenAI(api_key="sk-...")

# Talking to Ollama (local, offline)
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

The rest of your code is identical. This is intentional — it gives you a migration
path in both directions: start local, switch to cloud, or vice versa, by changing
one line.

**Industry term to know:** "OpenAI-compatible API" — you will see this everywhere.
Any local model server (Ollama, LM Studio, vLLM, llama.cpp server) that implements
this interface is "OpenAI-compatible." It is not an official standard, just a de facto one.

---

### Context Window — The Practical Constraint

For classic NLP models you worked with, sequence length was a hard architectural limit
(BERT: 512 tokens, early GPT-2: 1024 tokens). The same constraint exists for modern
LLMs, but the window is much larger — and different for local vs. cloud models.

| Model | Context window |
| --- | --- |
| GPT-4o | 128,000 tokens |
| Claude Sonnet 3.5 | 200,000 tokens |
| Gemma 3 12B (local) | 131,072 tokens |
| Gemma 3 4B (local) | 131,072 tokens |

Gemma 3 actually has a very large context window for a local model — 128K tokens.
The binding constraint in practice is RAM. Loading a 131K-token KV cache for a 12B
model requires significant memory. Ollama defaults to a shorter effective context to
stay within safe RAM limits. You can override this with `num_ctx` in the model options.

---

### Gemma 3 Model Sizes — Why We Chose 12B

Gemma 3 comes in four sizes (not 8B — that is a common misconception from the Llama family):

| Tag | Parameters | Disk size (Q4) | Best for |
| --- | --- | --- | --- |
| `gemma3:1b` | 1B | ~0.8 GB | Edge devices, very fast |
| `gemma3:4b` | 4B | ~3.3 GB | Fast iteration, lightweight tasks |
| `gemma3:12b` | 12B | ~8.1 GB | **Our choice** — quality + speed balance |
| `gemma3:27b` | 27B | ~17 GB | Highest quality, needs 32GB+ RAM |

For legal document extraction — where the model must follow precise instructions,
produce valid JSON, and handle complex clause language — 12B is the right tradeoff.
The 4B model is noticeably weaker at instruction following for structured tasks.

---

### What Happens When You Run `ollama pull gemma3:12b`

1. Ollama queries its model registry to find the model manifest
2. Downloads model metadata (layer hashes, architecture config)
3. Downloads each layer of the GGUF file in parallel chunks
4. Verifies checksums
5. Stores the model in `~/.ollama/models/`
6. Makes it available for `ollama run` or API calls

The model is pulled once and cached. Subsequent app launches load from disk in ~3 seconds.

---

### What Happens When You Run `ollama run gemma3:12b "..."`

1. Ollama loads the GGUF weights from disk into RAM (uses Apple Metal GPU on Apple Silicon automatically)
2. Tokenizes your input string using the model's built-in tokenizer
3. Runs the autoregressive generation loop (each forward pass produces one token)
4. Streams tokens to stdout as they are generated
5. Stops at the EOS (end of sequence) token

The generation loop is identical to what you know from seq2seq models — greedy/sampling
decoding over a very large vocabulary (Gemma 3 uses a 256k token vocab).

---

### Phase 1 — Completion Status

- [x] Ollama installed (v0.23.2) and running as a background daemon on port 11434
- [x] `gemma3:12b` pulled and cached at `~/.ollama/models/` (8.1 GB)
- [x] Model responds coherently to a legal domain prompt in the terminal
- [x] Token streaming observed (tokens print one at a time, not all at once)

**Model correction from plan:** The original plan specified `gemma3:8b` — this tag does
not exist. Gemma 3 sizes are 1B, 4B, 12B, 27B. We use `gemma3:12b` throughout the project.

---

## Phase 2 — Backend Skeleton

### What FastAPI Is and Why It Replaced Flask for AI Work

Flask was the Python backend standard for most of the last decade. FastAPI replaced it
for AI and ML work for two concrete reasons:

**1. Async by default.**
Flask is synchronous — one request blocks the thread until it finishes. If your endpoint
calls an LLM that takes 20 seconds to respond, that thread is stuck for 20 seconds. Under
load, this means your server grinds to a halt.

FastAPI is built on `asyncio` and `Starlette`. Endpoints can be declared `async def`,
which means while the model is generating tokens, the thread is free to handle other
requests. This matters enormously for LLM apps where latency is high.

**2. Automatic request/response validation via Pydantic.**
You define a Python class describing the shape of incoming data, and FastAPI validates,
parses, and documents it automatically:

```python
class AnalyzeRequest(BaseModel):
    text: str
```

If a request arrives without `text`, or with `text` as an integer, FastAPI returns a
clear 422 error with a description — no manual validation code needed. This same schema
also powers the auto-generated `/docs` UI (Swagger) that lets you test the API in a browser.

**The `/docs` endpoint is free.**
Run the server and open `http://localhost:8000/docs`. You get a fully interactive API
explorer with no extra work. For a portfolio project this is a valuable demo artifact.

---

### Pydantic — What It Is and Why It Matters

Pydantic is the data validation library FastAPI is built on. You will see it everywhere
in the modern Python AI ecosystem.

The core idea: define the shape of your data as a Python class, and Pydantic enforces it:

```python
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    text: str
```

When FastAPI receives a POST request, it passes the raw JSON body to Pydantic.
Pydantic checks that `text` exists and is a string. If valid, it returns a typed
`AnalyzeRequest` object. If invalid, it raises a structured error before your
function even runs.

This pattern — **schema-first validation at the boundary** — is the modern replacement
for writing `if "text" not in request.json` guards manually. It is also how the
OpenAI SDK defines its request/response types, and how most modern Python APIs are built.

---

### The OpenAI SDK Pointed at Ollama

The `openai` Python package is not tied to OpenAI's servers. It is an HTTP client that
speaks the Chat Completions protocol. You can point it at any server that implements
the same API — including Ollama running locally:

```python
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",          # Ollama ignores this but the SDK requires it
)
```

The call to generate a response is identical to what you would write for GPT-4:

```python
response = client.chat.completions.create(
    model="gemma3:12b",        # local model name instead of "gpt-4o"
    messages=[
        {"role": "user", "content": request.text},
    ],
)
```

**Why this design is important for the portfolio story:** The abstraction means you can
demo the app locally (offline, private) and switch to a cloud model for a client with
different constraints by changing one environment variable — `OLLAMA_HOST` and `MODEL`.
No application logic changes.

---

### Environment Variables — The Right Way to Configure an App

Notice that `main.py` reads configuration from environment variables, not hardcoded values:

```python
MODEL = os.getenv("MODEL", "gemma3:12b")
base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1"
```

`os.getenv("KEY", "default")` reads the variable named `KEY` from the environment.
If it is not set, it falls back to the default.

This is the **12-Factor App** pattern for configuration — a widely adopted standard for
building deployable software. The rule: anything that changes between environments
(dev, staging, prod) must come from the environment, not from source code.

In practice this means:

- Local dev: no env vars set, defaults kick in, talks to `localhost:11434`
- On-premises server: `OLLAMA_HOST=http://192.168.1.50:11434` set in the shell
- Docker: `OLLAMA_HOST=http://ollama:11434` set in `docker-compose.yml`

The application code never changes. Only the environment does.

---

### What the Health Check Endpoint Does

`GET /health` is a **liveness check** — a standard backend pattern that answers:
"Is this service and everything it depends on actually running?"

```json
{
  "status": "ok",
  "ollama_reachable": true,
  "model": "gemma3:12b"
}
```

It is not a user-facing feature. It is infrastructure tooling used by:

- **Kubernetes / Docker** — hits `/health` every 30 seconds; restarts the container if it fails
- **Load balancers** — only routes traffic to instances that pass the check
- **CI/CD pipelines** — waits for `/health` to return 200 before running integration tests
- **Monitoring tools** — pages on-call if the endpoint goes dark

For local development, it is useful as a quick sanity check: before debugging a slow
`/analyze` response, hit `/health` first to confirm Ollama is actually reachable.

---

### Phase 2 — Completion Status

- [x] Project directory structure created (`backend/`, `frontend/`, `prompts/`, `sample_docs/`)
- [x] Python 3.13 virtual environment created at `.venv/`
- [x] Dependencies installed: `fastapi`, `uvicorn`, `openai`
- [x] `requirements.txt` created
- [x] `backend/main.py` written with `/health` and `/analyze` endpoints
- [x] `GET /health` returns `ollama_reachable: true` and correct model name
- [x] `POST /analyze` returns a coherent legal domain response from `gemma3:12b`

**What the response confirmed:** The model reasons about legal concepts correctly and at
a level of detail that is useful for clause extraction. The next step (Phase 3) replaces
the raw text input with a PDF upload and extracted text.

**Key thing to notice:** The response took several seconds but arrived as one complete
block. That is because streaming is not enabled yet — the server waited for the full
response before returning it. Phase 4 fixes this.

---

## Phase 3 — PDF Parsing

### Why PDF Extraction Is Harder Than It Looks

A PDF is not a document format. It is a **page description language** — a set of
instructions for placing ink on a page at precise coordinates. There is no concept
of "words," "paragraphs," or "reading order" in the file format itself.

When pdfplumber extracts text, it is reconstructing prose from a list of
`(character, x, y)` tuples. This works well for simple documents but breaks on:

- Multi-column layouts (columns get interleaved)
- Tables (cell content merges into garbled rows)
- Scanned PDFs (no text layer at all — just images)
- Headers/footers (appear mid-sentence in the extracted flow)
- Justified text (extra spaces inserted for alignment)

For legal contracts — which are almost always single-column, machine-generated PDFs —
pdfplumber is reliable. Scanned documents would require OCR (e.g., `pytesseract`),
which is out of scope for this project.

---

### What pdfplumber Does Differently

pdfplumber is built on `pdfminer.six` (a lower-level PDF parsing library) and adds
layout analysis on top. The key option we use:

```python
page.extract_text(layout=True)
```

`layout=True` tells pdfplumber to use character coordinates to reconstruct spatial
layout — it places spaces proportionally based on the gap between characters. This
preserves indentation and column alignment but produces excessive horizontal whitespace
that wastes tokens when sent to an LLM.

Without `layout=True`, pdfplumber uses a simpler left-to-right, top-to-bottom scan
which can merge words incorrectly when text is not linearly arranged.

For single-column legal documents, `layout=True` is the right choice — we just clean
the whitespace afterward.

---

### The Cleaning Pipeline

The raw extraction from a two-page NDA produced 13,078 characters. After cleaning: 5,454
characters — a 58% reduction. The word count stayed at 763, meaning no content was lost,
only formatting noise.

The three cleaning steps in `backend/parser.py`:

```python
# 1. Collapse runs of spaces/tabs within each line
text = re.sub(r"[ \t]{2,}", " ", text)

# 2. Strip lines that are only whitespace (layout artifacts)
text = re.sub(r"(?m)^[ \t]+$", "", text)

# 3. Strip standalone page numbers
text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
```

**Why this matters for LLMs:** Most local models are billed by tokens (or practically
limited by context window). Sending 13k characters when 5.4k conveys the same content
wastes ~2,000 tokens per document. At scale — or with smaller context windows — this
directly affects whether the document fits in one pass.

---

### FastAPI File Uploads — UploadFile

Accepting a file upload in FastAPI requires two things not needed for JSON endpoints:

**1. `python-multipart` package** — FastAPI uses `multipart/form-data` encoding for
file uploads (the same encoding HTML forms use). The `python-multipart` package handles
parsing this format. Without it, FastAPI raises a `RuntimeError` at startup.

**2. The `UploadFile` type** — FastAPI's typed wrapper around an uploaded file:

```python
from fastapi import File, UploadFile

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    pdf_bytes = await file.read()   # read the raw bytes
    text = extract_text(pdf_bytes)  # pass to pdfplumber
```

Notice `async def` and `await file.read()`. File I/O is non-blocking in FastAPI — the
`await` yields control while the bytes are read, freeing the event loop for other
requests. This is the practical difference between `def` and `async def` endpoints.

`UploadFile` also gives you:

- `file.filename` — original filename from the client
- `file.content_type` — MIME type (`application/pdf`)
- `file.size` — file size in bytes (FastAPI 0.100+)

---

### How curl Sends a File Upload

Testing a file upload endpoint from the terminal uses `-F` (form data), not `-d` (raw body):

```bash
# JSON body (Phase 2)
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"text": "..."}'

# File upload (Phase 3)
curl -X POST http://localhost:8000/analyze \
  -F "file=@sample_docs/sample_nda.pdf"
```

The `-F "file=@path"` syntax tells curl to read the file at `path` and send it as a
`multipart/form-data` field named `file`. The `@` prefix means "read from file."

---

### Phase 3 — Completion Status

- [x] `pdfplumber` and `python-multipart` installed
- [x] `backend/parser.py` written with `extract_text()` and `_clean()` functions
- [x] Sample NDA PDF generated (`sample_docs/sample_nda.pdf`) — 2 pages, 8 clauses
- [x] Parser tested standalone: 13,078 chars raw → 5,454 chars cleaned, 763 words preserved
- [x] `backend/main.py` updated — `/analyze` now accepts `UploadFile` instead of raw text
- [x] End-to-end test passed: `curl -F "file=@sample_nda.pdf"` returns a coherent NDA summary
- [x] VSCode interpreter set to `.venv` — all packages resolve without warnings

**What the model did with the extracted text:** It correctly identified both parties,
the 3-year term, the Net 30 payment clause, the indefinite indemnification clause (a
risk), governing law (California), and the Exhibit A permitted disclosures. The
structured extraction in Phase 5 will formalize this into JSON fields.

---

## Phase 4 — Streaming

### Why Streaming Exists

LLMs generate text one token at a time — each forward pass produces a single token,
which is then fed back as input for the next pass. This is the same autoregressive
loop you know from seq2seq models.

Without streaming, the server runs the full generation loop internally, waits for the
EOS token, assembles the complete string, and then sends it to the client in one
HTTP response. For a 400-token response at 15 tokens/second, that is a **27-second
wait** before anything appears on screen. The UI looks frozen. Users assume it crashed.

With streaming, each token is forwarded to the client immediately after it is generated.
The user sees text appearing word by word — same total time, but perceived as
instantaneous because feedback starts in under a second.

**This is not a cosmetic feature.** Streaming is the primary mechanism that makes
LLM interfaces feel interactive rather than broken. Every production LLM API
(OpenAI, Anthropic, Gemini) supports it, and every real LLM app uses it.

---

### Server-Sent Events (SSE)

The streaming protocol we use is **Server-Sent Events (SSE)** — a standard HTTP
mechanism for servers to push a stream of text chunks to a client over a single
long-lived connection.

The wire format is plain text, one chunk per HTTP response body fragment:

```text
Here
 is
 a
 summary
...
```

SSE is simpler than WebSockets for this use case because:

- It is unidirectional (server → client only) — which is all we need
- It works over standard HTTP — no protocol upgrade required
- Browsers support it natively via `EventSource`
- FastAPI supports it natively via `StreamingResponse`

**WebSockets** would be needed if the client also needs to send messages mid-stream
(e.g., "stop generating"). For read-only token streaming, SSE is the right tool.

---

### Python Generators — The Key Concept

The streaming implementation uses a **generator function** — a function that `yield`s
values one at a time instead of returning them all at once:

```python
def _stream_llm(text: str):
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[...],
        stream=True,          # Ollama sends chunks instead of one response
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token is not None:
            yield token       # send this token to the client immediately
```

When `stream=True`, the OpenAI SDK returns an iterator instead of a complete response.
Each iteration of the `for` loop makes a network call to Ollama, receives one chunk,
and returns control to the loop. The `yield` inside sends that chunk downstream.

`StreamingResponse` in FastAPI accepts any Python generator or async generator and
forwards each yielded value directly to the HTTP response body as it arrives:

```python
return StreamingResponse(
    _stream_llm(text),
    media_type="text/plain",
)
```

The connection stays open until the generator is exhausted (when Ollama sends the
EOS token and the stream ends).

---

### What `--no-buffer` Does in curl

```bash
curl --no-buffer -X POST http://localhost:8000/analyze -F "file=@contract.pdf"
```

By default, curl buffers output — it collects chunks and prints them in batches.
`--no-buffer` disables this, printing each chunk immediately as it arrives from the
server. Without it, streaming output looks like a delayed dump, making it impossible
to verify that streaming is actually working.

In a browser, this buffering issue does not exist — browsers render streamed content
progressively by default. `--no-buffer` is only a curl-specific concern for testing.

---

### The delta.content Pattern

The OpenAI streaming response format wraps each token in a `delta` object:

```python
chunk.choices[0].delta.content   # the token text, or None for control chunks
```

`delta` means "the change since the last chunk." For content tokens it is the new
text. For the final chunk it is `None` (signaling end of stream). The `if token is
not None` guard prevents forwarding those control chunks downstream.

This pattern is identical whether you are calling OpenAI, Anthropic's API, or Ollama.
The delta wrapper is part of the OpenAI-compatible spec.

---

### Phase 4 — Completion Status

- [x] `_stream_llm()` generator function added to `backend/main.py`
- [x] `/analyze` endpoint returns `StreamingResponse` instead of a JSON dict
- [x] `stream=True` passed to the Ollama API call
- [x] Tested with `curl --no-buffer` — tokens visibly printed one at a time
- [x] Full NDA summary streamed and completed correctly

**What changes in Phase 5:** The streaming response is currently plain text. In Phase 5
we add a system prompt instructing the model to return JSON, and add validation to
ensure the response is parseable. The streaming will be preserved — we stream the JSON
string token by token and only parse it once the stream is complete.

---

## Phase 5 — Structured Extraction

### The Core Problem: LLMs Output Prose, Not Data

A raw LLM response is a string. Your application needs a Python dict. The gap between
those two things is where most LLM application engineering lives.

Cloud models like GPT-4o have a `response_format={"type": "json_object"}` parameter
that enforces JSON output at the decoding level — the model is constrained to only
generate tokens that form valid JSON. Local models in Ollama do support a `format`
parameter (Ollama-specific, not OpenAI-compatible), but it is not as reliable for
complex schemas. The portable, model-agnostic approach — and the one used in
production at most companies — is **prompt engineering + validation + retry**.

---

### The System Prompt — What It Does and Why

The Chat Completions API has two message roles relevant here:

- `system` — instructions to the model about how to behave. The model treats this as
  its operating context, not as something to respond to.
- `user` — the actual input to process.

The system prompt in `prompts/legal_extraction.txt` does four things:

**1. Defines the role** — "You are a legal document analysis assistant." This primes
the model to use legal vocabulary and reasoning rather than generic language.

**2. Gives an explicit output format** — the JSON schema with field names, types, and
examples. Without this, the model decides the shape of the output. With it, the output
is consistent across documents.

**3. States the rules unambiguously** — "Return ONLY the raw JSON object. No markdown.
No code blocks. No preamble." Local models frequently wrap JSON in triple backticks
(```` ```json ``` ````). The rule must be stated explicitly.

**4. Sets `temperature=0.0`** — temperature controls randomness in token sampling.
At 0.0, the model always picks the highest-probability token (greedy decoding). This
makes the output deterministic — the same document produces the same JSON every time.
For structured extraction, consistency matters more than creativity.

---

### Prompt Engineering Patterns for Structured Output

These are patterns that work reliably with local models for JSON extraction:

**Show the schema, not just the field names:**

```text
"risky_clauses": ["each clause that could disadvantage one party, with a brief explanation"]
```

Describing what the value should look like (not just the key name) dramatically
reduces hallucination and empty-array responses.

**Set null behavior explicitly:**

```text
Use null (not "null", not "N/A", not "") for missing fields.
```

Without this, models return inconsistent null representations — all four variants
above appear regularly.

**Prevent empty arrays:**

```text
Arrays must never be empty — if nothing was found, write ["None identified"].
```

Empty arrays (`[]`) break downstream rendering code. The sentinel value
`["None identified"]` is easier to handle.

**Close the loop on the output contract:**

```text
Your entire response must be parseable by Python's json.loads().
```

Referencing a specific function makes the constraint concrete rather than abstract.

---

### The Validator — Defensive Parsing

Even with a well-written prompt, local models occasionally:

1. Wrap the JSON in markdown code fences: ```` ```json {...} ``` ````
2. Add a sentence before the JSON: `"Here is the analysis: {...}"`
3. Produce slightly malformed JSON (trailing comma, unquoted key)

`backend/validator.py` handles cases 1 and 2 with a two-step approach:

```python
# Step 1: strip markdown fences
cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

# Step 2: find the outermost { } pair and extract just that
start = cleaned.find("{")
end = cleaned.rfind("}")
candidate = cleaned[start : end + 1]

return json.loads(candidate)
```

Case 3 (malformed JSON) is handled by the retry logic — if `json.loads` raises, the
validator raises `ValueError`, which triggers a second model call with a stricter
instruction.

---

### The Retry Pattern

The retry is implemented as a **conversation continuation** — the failed response is
appended to the message history as an assistant turn, then a correction instruction
is added as a new user turn:

```python
messages.append({"role": "assistant", "content": raw})       # the bad response
messages.append({"role": "user",      "content": RETRY_SUFFIX})  # the correction
raw = _call_model(messages)
```

This is more effective than re-sending the original prompt from scratch because the
model can see what it did wrong. The retry suffix says:

> "Your previous response was not valid JSON. Return ONLY the raw JSON object with
> no explanation, no markdown, no code blocks."

The model sees its own bad output and self-corrects. In practice, this handles ~95%
of the failure cases that get past the prompt. The remaining 5% (truly broken JSON)
returns an HTTP 500 with the parse error included.

---

### temperature=0.0 — Why It Matters for Extraction

Temperature is the softmax temperature applied during token sampling. At `temperature=1.0`
(the default), the model samples from the full probability distribution — creative,
varied, but non-deterministic. At `temperature=0.0`, it always picks the single
highest-probability token (greedy decoding).

For **structured extraction**, determinism is the right tradeoff:

- Same document → same JSON every time (testable, debuggable)
- No random variation in field names or null vs. string for missing values
- Consistent enough to write tests against

For **creative tasks** (writing, brainstorming, summarization), higher temperature
produces better results. The right temperature is task-dependent — extraction tasks
universally benefit from 0.0.

---

### What Was Extracted from the Sample NDA

The model correctly identified on the first attempt:

| Field | Extracted value |
| --- | --- |
| `parties` | Acme Technologies Inc., Horizon Legal Partners LLP |
| `effective_date` | 2024-01-15 (correct YYYY-MM-DD format) |
| `termination_date` | null (no specific date in the document — correct) |
| `payment_terms` | Net 30, 1.5%/month late interest |
| `key_obligations` | 4 obligations accurately extracted |
| `risky_clauses` | Indefinite indemnification correctly flagged as high risk |
| `governing_law` | State of California |
| `summary` | Accurate 3-sentence summary |
| `follow_up_questions` | 3 relevant legal questions |

---

### Phase 5 — Completion Status

- [x] `prompts/legal_extraction.txt` — system prompt with schema, rules, and null handling
- [x] `backend/prompt.py` — loads prompt from file, assembles message list
- [x] `backend/validator.py` — strips markdown fences, extracts JSON object, raises on failure
- [x] `backend/main.py` updated — `temperature=0.0`, first attempt + retry on failure
- [x] `/analyze` returns structured JSON with `filename`, `result`, and `attempts` fields
- [x] Tested on `sample_nda.pdf` — valid JSON on first attempt, all 9 fields correctly populated

**What is still missing:** The response currently arrives as a single JSON blob after
the model finishes (no streaming). Phase 7 (Streamlit) will stream the JSON string
token by token and parse it client-side once the stream is complete, combining the
UX benefit of Phase 4 with the structure of Phase 5.

---

## Phase 6 — Context Window Handling

### Why Chunking Is Needed

Gemma 3 12B has a 131,072-token context window — large by local model standards, but
not unlimited. The binding constraint in practice is RAM: the KV cache (the attention
state for all previous tokens) grows linearly with context length. Ollama defaults to
a shorter effective window to stay within safe memory limits on typical hardware.

Beyond memory, there is a quality argument: models tend to "lose focus" in very long
contexts. Important information buried in the middle of a 100,000-token document is
less reliably extracted than the same information in a shorter prompt. For critical
legal documents, smaller focused chunks often produce better extraction than one
massive prompt.

The threshold we use — 60,000 tokens (240,000 characters) — leaves headroom for the
system prompt, the model's response, and the KV cache. This fits the vast majority of
legal documents (NDAs, employment contracts, vendor agreements) in one pass. Chunking
activates for very long documents like M&A agreements or multi-exhibit contracts.

---

### Token Counting Without tiktoken

`tiktoken` is OpenAI's tokenizer library. It produces accurate token counts for GPT
models but gives incorrect counts for Gemma 3, which uses a SentencePiece tokenizer
with a 256,000-token vocabulary — a completely different tokenization scheme.

The portable alternative: **character-based approximation**.

```python
CHARS_PER_TOKEN = 4
def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN
```

The `~4 characters per token` ratio holds reasonably well across English prose for
most modern LLM tokenizers. It is not perfectly accurate — short words tokenize
closer to 1 char/token, long technical terms closer to 6 — but for the purpose of
deciding "is this document too long to fit in one prompt?" it is accurate enough and
requires zero dependencies.

For production systems where accuracy matters (billing, quota enforcement), you would
use the model's actual tokenizer. For a local offline app where the only consequence
of a wrong estimate is an unnecessary extra chunk, the approximation is the right
tradeoff.

---

### The Chunking Strategy — Paragraph Boundaries

The chunker splits on `\n\n` (paragraph breaks) rather than at a fixed character
offset. This matters for legal text where a single sentence can be 200 words long.
Splitting mid-sentence produces chunks that:

- Start without context (the subject was in the previous chunk)
- End abruptly, confusing the model about what clause is being analyzed

Paragraph-boundary splitting ensures each chunk contains complete thoughts. The
trade-off: chunk sizes are uneven. That is acceptable — a chunk that is 80% of the
limit is fine; only a chunk that exceeds the limit is a problem.

```python
paragraphs = re.split(r"\n\n+", text)
chunks: list[str] = []
current: list[str] = []
current_len = 0

for para in paragraphs:
    para_len = len(para) + 2
    if current and current_len + para_len > max_chars:
        chunks.append("\n\n".join(current))   # flush current chunk
        current = [para]                       # start a new one
        current_len = para_len
    else:
        current.append(para)
        current_len += para_len
```

---

### The Merge Strategy — Field by Field

Each chunk produces a complete JSON object with all nine fields. The merge function
combines them by field type:

| Field | Merge strategy | Why |
| --- | --- | --- |
| `parties` | Union, deduplicate | Same party appears in multiple clauses |
| `effective_date` | First non-null | Only one effective date per contract |
| `termination_date` | First non-null | Only one termination date |
| `payment_terms` | First non-null | Usually in one specific clause |
| `key_obligations` | Union, deduplicate | Spread across all sections |
| `risky_clauses` | Union, deduplicate | Any clause can be risky |
| `governing_law` | First non-null | One jurisdiction per contract |
| `summary` | Join in chunk order | Each chunk summarizes its section |
| `follow_up_questions` | Union, deduplicate | Each chunk contributes questions |

The `"None identified"` sentinel (set in the prompt) allows the union logic to
distinguish "the model looked and found nothing" from "this field was missing."

---

### Configurable Threshold via Environment Variable

The chunk limit is controlled by `CHUNK_TOKENS`:

```bash
# Default: 60,000 tokens (production use)
uvicorn backend.main:app --port 8000

# Lowered for testing: forces chunking on small documents
CHUNK_TOKENS=700 uvicorn backend.main:app --port 8000
```

This follows the same 12-Factor App pattern from Phase 2 — behavior that changes
between environments (or between testing and production) lives in the environment,
not in the code. It also means you can tune the chunk size for different hardware
without touching a single line of Python.

---

### Phase 6 — Completion Status

- [x] `backend/chunker.py` written: `estimate_tokens`, `chunk_text`, `merge_results`
- [x] `sample_docs/sample_employment.pdf` generated — 2,851 tokens, 9 clauses
- [x] Chunker unit-tested: 2,851-token doc → 5 clean chunks at 700-token limit
- [x] `backend/main.py` updated — single-chunk and multi-chunk paths share `_analyze_chunk`
- [x] `/health` now reports `chunk_token_limit` for observability
- [x] Single-chunk path tested on NDA: `chunks: 1`, correct result
- [x] Multi-chunk path tested on employment contract: `chunks: 5`, merged result with
      18 obligations, 14 risky clauses, 15 follow-up questions — all correctly deduplicated

**What the multi-chunk test revealed:** The merge produced a few generic party labels
("Employee", "Company") alongside the real names. A production system would post-process
these with a deduplication step that normalizes aliases. This is a known limitation of
chunk-level extraction and a good talking point in portfolio discussions.

---

## Phase 7 — Streamlit Frontend

### What Streamlit Is

Streamlit is a Python library that turns a plain Python script into an interactive web
application — no HTML, no CSS, no JavaScript required. You write Python, and Streamlit
renders it as a browser UI.

This is a deliberate trade-off: you give up full UI control in exchange for extreme
development speed. For data science and AI prototypes, this trade-off is almost always
worth it. A Streamlit app that demonstrates a working AI pipeline is worth far more in
a portfolio than a half-built React frontend.

**Why not Flask or Django?**
Flask/Django are general-purpose web frameworks. They give you full control but require
you to write routes, templates, and frontend code separately. Streamlit is purpose-built
for data apps — it assumes you want widgets, charts, and data displays, so those are
first-class concepts, not add-ons.

---

### How Streamlit's Execution Model Works

This is the most important concept to understand, because it is different from every
other framework you have used before.

**Streamlit reruns the entire script from top to bottom on every user interaction.**

Every time the user clicks a button, uploads a file, or interacts with any widget,
Streamlit executes `app.py` from line 1 to the end, completely fresh. There is no
persistent event loop, no callbacks, no DOM diffing.

```text
User clicks button
    → Python script runs top to bottom
    → Streamlit diffs the new UI against the old one
    → Browser updates only the changed parts
```

This means:

- **Every widget call both renders the widget AND returns its current value.**
  `uploaded = st.file_uploader(...)` renders the uploader and gives you the file.
- **Conditional rendering is just an `if` statement.**
  `if uploaded: st.button("Analyze")` only shows the button when a file is selected.
- **Code after `st.stop()` never runs.** Used to halt execution on errors.

This model feels strange at first but makes logic extremely readable — the script reads
top-to-bottom like a description of what the page should look like right now.

---

### Session State

Since the script reruns completely on every interaction, local variables are reset each
time. For values that need to persist across reruns (e.g., analysis results), Streamlit
provides `st.session_state` — a dictionary that survives reruns within the same browser
session.

In this app we did not need session state because the results are displayed immediately
after the API call completes and the button re-render naturally holds the result in scope.
In more complex apps (multi-step flows, chat history), `st.session_state` becomes
essential.

---

### The Frontend-Backend Split

This app follows a clean separation of concerns that mirrors production architecture:

```text
Browser (Streamlit at :8501)
    ↕  HTTP POST /analyze  (multipart/form-data)
FastAPI backend (:8000)
    ↕  HTTP POST /v1/chat/completions
Ollama (:11434)
    ↕  loads weights from disk
gemma3:12b model
```

Streamlit is just a frontend that calls the FastAPI backend over HTTP using the
`requests` library — exactly the same call you would make from `curl` or a React app.
This means:

- The backend is independently testable (we tested it with `curl` throughout development)
- The frontend can be swapped out without touching the backend
- In production, the frontend and backend could run on different machines

This architecture pattern — thin frontend + HTTP API + model server — is the standard
pattern for AI applications at every scale, from prototypes to production systems.

---

### The `requests` Library

`requests` is Python's standard HTTP client library. It is to HTTP what `psycopg2` is
to PostgreSQL — the tool you reach for to talk to an HTTP service from Python code.

```python
response = requests.post(
    "http://localhost:8000/analyze",
    files={"file": (filename, file_bytes, "application/pdf")},
    timeout=300,
)
```

Key parameters used here:

- `files=` — sends the data as `multipart/form-data`, which is how browsers upload
  files. FastAPI's `UploadFile` on the receiving end expects exactly this format.
- `timeout=300` — waits up to 5 minutes for a response. Without this, `requests`
  blocks forever. Long-running AI calls need an explicit timeout.

The response object has `.status_code` (HTTP status) and `.json()` (parsed response
body). Always check the status code before calling `.json()` to avoid confusing errors.

---

### Streamlit Layout Primitives

The UI uses four layout tools:

| Tool | What it does |
| --- | --- |
| `st.sidebar` | A persistent left panel — good for config and status that doesn't change per analysis |
| `st.columns([1, 2])` | Splits the page into proportional columns — used for the key-details label/value table |
| `st.expander(label)` | A collapsible section — good for secondary information (obligations, clauses, raw JSON) |
| `st.spinner(msg)` | A loading indicator that shows while a `with` block runs |

These are the primitives you will use in 90% of Streamlit apps. The full widget
library includes charts, maps, data tables, and more — but for a document analysis
app, text and layout primitives are what matter.

---

### Health Check as a UI Feature

The sidebar calls `/health` on every page load and renders the result as a live
status indicator. This turns a backend engineering concept (the health check endpoint
built in Phase 2) into a direct user-facing feature: the user can see at a glance
whether Ollama is running before uploading a document.

This is a good design pattern: backend observability endpoints and frontend status
indicators should be linked, not built separately. One source of truth, two consumers.

---

### Phase 7 Milestone Checklist

- [x] Streamlit installed and `frontend/app.py` created
- [x] Sidebar shows live Ollama status, model name, and chunk limit from `/health`
- [x] File uploader accepts PDF, shows filename and size
- [x] Analyze button calls `/analyze`, shows spinner during wait
- [x] Results: summary, key details table, obligations, risky clauses, follow-up questions
- [x] Risky clauses section shows warning banner when clauses are present
- [x] Raw JSON expander for full API transparency
- [x] Tested with `sample_nda.pdf` — correct parties, date, 4 obligations, 3 risky clauses
- [x] Full stack verified end-to-end in browser

---

## Phase 8 — Portfolio Polish

### What This Phase Is About

Phase 8 is not about adding features — it is about making the work you already did
legible to people who were not there when you built it. A great project with a poor
README is invisible. A great README turns a working prototype into a portfolio asset.

The three things that matter most to a recruiter or hiring manager landing on your repo:

1. **What does it do?** — answered by the title, one-line description, and screenshots
2. **How do I run it?** — answered by the Setup section
3. **Does the author know what they are doing?** — answered by the architecture diagram,
   the tech stack table, and the design decisions section

If those three questions are answered in the first scroll, the repo does its job.

---

### Git and Version Control Fundamentals

This phase introduced `git` as a version control tool for the first time in the project.
Key concepts used:

**`git init`** — Initializes an empty Git repository in the current directory. Creates
a hidden `.git/` folder that tracks all history. You only run this once per project.

**`.gitignore`** — A file that tells Git which files to never track. Critical entries
for a Python project:

```text
.venv/          ← virtual environment (hundreds of MB, fully reproducible from requirements.txt)
__pycache__/    ← compiled Python bytecode (auto-generated, never hand-edited)
.DS_Store       ← macOS filesystem metadata (irrelevant to the project)
.env            ← secrets and credentials (NEVER commit these)
.claude/        ← local Claude Code settings (machine-specific, not project code)
```

The rule: commit source code and configuration. Never commit generated files, large
binaries, or secrets.

**`git add`** — Stages files for the next commit. You explicitly choose what goes in,
which is why `.gitignore` matters — it prevents accidental staging of files you never
want tracked.

**`git commit`** — Saves a snapshot of all staged files with a message. The message
should explain *why* the change was made, not *what* changed (the diff shows that).

**`git push`** — Sends local commits to a remote repository (GitHub in this case).

---

### SSH vs HTTPS Authentication

When pushing to GitHub, there are two ways to authenticate:

**HTTPS** — Uses your GitHub username and a Personal Access Token (PAT). The URL looks
like `https://github.com/user/repo.git`. Requires a token because GitHub removed
password authentication in 2021.

**SSH** — Uses a key pair: a private key on your machine (`~/.ssh/id_ed25519`) and a
public key registered with GitHub. The URL looks like `git@github.com:user/repo.git`.
No password needed after setup — the handshake is cryptographic.

This project used SSH because the machine already had an `id_ed25519` key pair. SSH is
generally preferred for developer machines because it is more convenient (no token
management) and more secure (private key never leaves your machine).

---

### README as a Technical Document

A good README for an AI project should cover:

| Section | Purpose |
| --- | --- |
| Title + one-liner | Immediate orientation |
| Screenshots | Show don't tell — the fastest way to convey what the app does |
| Why offline / motivation | The design constraint that shapes all decisions |
| What it extracts | Concrete output — makes the value proposition tangible |
| Tech stack | Signals technical choices and lets readers assess fit |
| Architecture diagram | Shows systems thinking, not just coding ability |
| Setup instructions | Proves the project actually runs |
| Configuration | Shows awareness of deployment concerns (12-Factor) |
| Limitations | Shows honesty and engineering maturity |

The limitations section is particularly important in a portfolio context. Listing known
limitations signals that you understand the system deeply, not just that you got it
working. Hiding limitations suggests the opposite.

---

### Mermaid Diagrams in GitHub

GitHub renders Mermaid diagrams natively in Markdown files — no plugin or external
tool needed. A fenced code block with the `mermaid` language tag becomes an interactive
diagram when viewed on GitHub. The opening fence is written as ` ```mermaid `
followed by the diagram definition, then a closing ` ``` `.

Key Mermaid concepts used in this project:

**`classDef`** — Defines a reusable style (fill color, stroke, text color):

```text
classDef backend fill:#059669,stroke:#047857,color:#FFFFFF
```

**`:::className`** — Applies a class to a specific node:

```text
API["FastAPI Backend\n:8000"]:::backend
```

**`%%{init: {...}}%%`** — Sets the theme and theme variables for the whole diagram.
The `base` theme is used when you want full color control via `classDef`.

**`subgraph`** — Groups nodes inside a labeled box. Used here to show all components
running on the same machine, reinforcing the offline architecture.

---

### Project Completion Summary

PrivateDoc AI is fully shipped. Here is what was built across all 8 phases:

| Phase | What was built |
| --- | --- |
| 1 | Local model running via Ollama (gemma3:12b) |
| 2 | FastAPI backend with health check and text endpoint |
| 3 | PDF parsing with pdfplumber and text cleaning |
| 4 | Streaming token output endpoint |
| 5 | Structured JSON extraction with prompt engineering and retry |
| 6 | Context window chunking and multi-chunk merge |
| 7 | Streamlit frontend — full UI end to end |
| 8 | README, screenshots, git history, live on GitHub |

---

### Phase 8 Milestone Checklist

- [x] `.gitignore` created — excludes `.venv`, `__pycache__`, `.DS_Store`, `.claude/`
- [x] `README.md` written — privacy pitch, screenshots, architecture, setup guide
- [x] Mermaid diagram with branded colors per component
- [x] `git init` and initial commit — 20 files, clean history
- [x] SSH remote configured and pushed to GitHub
- [x] `assets/` folder with 3 screenshots added to README
- [x] Repo live at `github.com/ftavafi/PrivateDocAI`
