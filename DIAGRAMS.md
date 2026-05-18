# PrivateDoc AI — Diagrams

Quick reference for all architecture diagrams. Full context and explanations are in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 1. System Architecture

```mermaid
graph TB
    subgraph USER_MACHINE["User's Machine (100% Local)"]
        subgraph FRONTEND["Layer 1 — Frontend (Streamlit :8501)"]
            UI["Browser UI\n─────────────\n• File upload widget\n• Streaming output\n• Structured results display"]
        end

        subgraph BACKEND["Layer 2 — Backend (FastAPI :8000)"]
            API["REST API\n─────────────\nPOST /analyze\nGET  /health"]
            PARSER["PDF Parser\n─────────────\npdfplumber\ntext extraction\nchunk splitting"]
            PROMPT["Prompt Builder\n─────────────\nsystem prompt\nJSON schema\nchunk assembly"]
            VALIDATOR["Response Validator\n─────────────\nJSON parse check\nretry on failure"]
        end

        subgraph MODEL_LAYER["Layer 3 — Model Server (Ollama :11434)"]
            OLLAMA["Ollama Server\n─────────────\nOpenAI-compatible API\nmodel lifecycle mgmt"]
            MODEL["Gemma 3 12B Q4_K_M\n─────────────\n~8GB on disk\nruns on Apple Silicon"]
        end
    end

    USER -->|"uploads PDF\nvia browser"| UI
    UI -->|"HTTP POST /analyze\nmultipart/form-data"| API
    API --> PARSER
    PARSER --> PROMPT
    PROMPT --> VALIDATOR
    VALIDATOR -->|"POST /v1/chat/completions\nlocalhost:11434"| OLLAMA
    OLLAMA --> MODEL
    MODEL -->|"token stream"| OLLAMA
    OLLAMA -->|"SSE token stream"| VALIDATOR
    VALIDATOR -->|"StreamingResponse"| API
    API -->|"SSE token stream"| UI
    UI -->|"renders tokens\nin real time"| USER

    style USER_MACHINE fill:#f0f4ff,stroke:#4a6fa5,stroke-width:2px
    style FRONTEND fill:#e8f5e9,stroke:#388e3c
    style BACKEND fill:#fff3e0,stroke:#f57c00
    style MODEL_LAYER fill:#fce4ec,stroke:#c62828
```

---

## 2. Data Flow

```mermaid
flowchart LR
    A([PDF Upload]) --> B[pdfplumber\nextracts text]
    B --> C{Token count\n> 6000?}
    C -- No --> D[Single prompt\nbuilt]
    C -- Yes --> E[Split into\nchunks]
    E --> F[Analyze each\nchunk separately]
    F --> G[Merge partial\nresults]
    D --> H[System prompt\n+ JSON schema\n+ document text]
    G --> H
    H --> I[Ollama API call\nstream=True]
    I --> J[Token stream\nSSE to browser]
    J --> K[Final JSON\nassembled]
    K --> L([Structured Output\nParties · Dates\nObligations · Risks\nSummary])
```

---

## 3. Request Sequence (Upload → Streaming Output)

```mermaid
sequenceDiagram
    actor User
    participant ST as Streamlit<br/>:8501
    participant FA as FastAPI<br/>:8000
    participant PL as pdfplumber
    participant OL as Ollama<br/>:11434
    participant GM as Gemma 3 12B

    User->>ST: uploads PDF file
    ST->>FA: POST /analyze (multipart/form-data)
    FA->>PL: extract_text(pdf_bytes)
    PL-->>FA: raw_text (string)
    FA->>FA: count_tokens(raw_text)

    alt text fits in context window
        FA->>FA: build_prompt(raw_text)
    else text too long
        FA->>FA: chunk_text(raw_text)
        loop for each chunk
            FA->>FA: build_prompt(chunk)
        end
    end

    FA->>OL: POST /v1/chat/completions (stream=True)
    OL->>GM: forward prompt
    
    loop token generation
        GM-->>OL: next token
        OL-->>FA: SSE chunk
        FA-->>ST: StreamingResponse chunk
        ST-->>User: token appears in UI
    end

    FA->>FA: validate_json(full_response)

    alt valid JSON
        FA-->>ST: structured result
        ST-->>User: formatted output
    else invalid JSON
        FA->>OL: retry with stricter prompt
        OL-->>FA: corrected response
        FA-->>ST: structured result
    end
```

---

## 4. Context Window Decision Logic

```mermaid
flowchart TD
    A[Document loaded] --> B[Estimate token count\n~4 chars per token]
    B --> C{Tokens < 6000?}
    C -- Yes --> D[Single-pass analysis\nFull document in one prompt]
    C -- No --> E[Chunk document\nby paragraph boundaries\n~4000 tokens per chunk]
    E --> F[Analyze Chunk 1]
    E --> G[Analyze Chunk 2]
    E --> H[Analyze Chunk N]
    F --> I[Merge Results\n• Combine party lists\n• Union risky clauses\n• Concatenate obligations\n• Summarize summaries]
    G --> I
    H --> I
    D --> J[Final structured JSON]
    I --> J
```

---

## 5. Component Ports at a Glance

```mermaid
graph LR
    Browser["Browser\nlocalhost:8501"] <-->|HTTP| Streamlit["Streamlit\n:8501"]
    Streamlit <-->|"HTTP POST /analyze\nSSE stream"| FastAPI["FastAPI\n:8000"]
    FastAPI <-->|"POST /v1/chat/completions\nSSE stream"| Ollama["Ollama\n:11434"]
    Ollama --- Model["Gemma 3 12B\nQ4_K_M\n~/.ollama/models/"]
```
