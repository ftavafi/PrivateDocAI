import requests
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="PrivateDoc AI",
    page_icon="",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("PrivateDoc AI")
    st.markdown("**100% offline legal document review.**")
    st.markdown(
        "Your documents never leave your machine. "
        "The AI model runs locally via [Ollama](https://ollama.com)."
    )
    st.divider()

    # Live health check
    st.subheader("System Status")
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=3).json()
        if health.get("ollama_reachable"):
            st.success("Ollama connected")
        else:
            st.error("Ollama unreachable — is it running?")
        st.caption(f"Model: `{health.get('model', '—')}`")
        st.caption(f"Chunk limit: `{health.get('chunk_token_limit', '—'):,}` tokens")
    except requests.exceptions.ConnectionError:
        st.error("Backend offline — start FastAPI first.")
    except Exception as e:
        st.warning(f"Health check failed: {e}")

    st.divider()
    st.caption("Phase 7 — Streamlit Frontend")

# ── Main ─────────────────────────────────────────────────────────────────────
st.header("Legal Document Analyzer")
st.markdown(
    "Upload a PDF contract or agreement. "
    "The model extracts key information and flags risky clauses."
)

uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded is not None:
    st.info(f"Selected: **{uploaded.name}** ({len(uploaded.getvalue()):,} bytes)")

    if st.button("Analyze Document", type="primary"):
        with st.spinner("Analyzing — this may take a minute for large documents…"):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/analyze",
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                    timeout=300,
                )
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the backend. Start FastAPI with `uvicorn backend.main:app`.")
                st.stop()

        if response.status_code != 200:
            st.error(f"Backend error {response.status_code}: {response.json().get('detail', response.text)}")
            st.stop()

        data = response.json()
        result = data["result"]

        # ── Meta ──────────────────────────────────────────────────────────
        st.success(
            f"Done — {data['token_estimate']:,} tokens, "
            f"{data['chunks']} chunk(s) processed."
        )

        # ── Summary ───────────────────────────────────────────────────────
        st.subheader("Summary")
        st.write(result.get("summary") or "_No summary returned._")

        # ── Key fields table ──────────────────────────────────────────────
        st.subheader("Key Details")
        fields = {
            "Parties":          ", ".join(result.get("parties") or []) or "—",
            "Effective Date":   result.get("effective_date") or "—",
            "Termination Date": result.get("termination_date") or "—",
            "Payment Terms":    result.get("payment_terms") or "—",
            "Governing Law":    result.get("governing_law") or "—",
        }
        col1, col2 = st.columns([1, 2])
        with col1:
            for label in fields:
                st.markdown(f"**{label}**")
        with col2:
            for value in fields.values():
                st.markdown(value)

        # ── Key obligations ───────────────────────────────────────────────
        obligations = result.get("key_obligations") or []
        with st.expander(f"Key Obligations ({len(obligations)})", expanded=True):
            if obligations and obligations != ["None identified"]:
                for item in obligations:
                    st.markdown(f"- {item}")
            else:
                st.write("None identified.")

        # ── Risky clauses ─────────────────────────────────────────────────
        risky = result.get("risky_clauses") or []
        risky_clean = [r for r in risky if r != "None identified"]
        label = f"Risky Clauses ({len(risky_clean)})"
        with st.expander(label, expanded=bool(risky_clean)):
            if risky_clean:
                st.warning("Review these clauses carefully before signing.")
                for item in risky_clean:
                    st.markdown(f"- {item}")
            else:
                st.success("No risky clauses flagged.")

        # ── Follow-up questions ───────────────────────────────────────────
        questions = result.get("follow_up_questions") or []
        questions_clean = [q for q in questions if q != "None identified"]
        with st.expander(f"Suggested Follow-Up Questions ({len(questions_clean)})"):
            if questions_clean:
                for q in questions_clean:
                    st.markdown(f"- {q}")
            else:
                st.write("None suggested.")

        # ── Raw JSON ──────────────────────────────────────────────────────
        with st.expander("Raw JSON (full API response)"):
            st.json(data)
