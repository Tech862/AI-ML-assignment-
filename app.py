import pandas as pd
import re
import streamlit as st

from document_intelligence import MAX_FILE_SIZE, analyze_document, process_uploaded_file
from storage import (complete_document, delete_document, get_document, init_db,
                     list_documents, save_document)

st.set_page_config(page_title="Document Intelligence", page_icon="📄", layout="wide")
init_db()

st.markdown("""
<style>
.stApp { --text-color:#172033; --background-color:#f4f7fb; --secondary-background-color:#fff;
  --primary-color:#315bea; color:#172033; background:#f4f7fb; }
[data-testid="stAppViewContainer"], [data-testid="stHeader"] { background:#f4f7fb; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid #e2e8f0; }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stCaptionContainer"], label, [data-testid="stMetricLabel"],
[data-testid="stMetricValue"] { color:#172033 !important; }
h1,h2,h3,h4 { color:#111827 !important; letter-spacing:-.025em; }
[data-testid="stMetric"] { background:#fff; color:#172033; padding:16px 18px;
  border:1px solid #e2e8f0; border-radius:14px; box-shadow:0 2px 8px #0f172a0a; }
[data-testid="stMetricLabel"] p { color:#526078 !important; font-weight:600; }
[data-testid="stMetricValue"] { color:#172033 !important; }
[data-testid="stFileUploader"] { background:#fff; padding:16px; border:1px dashed #9aacc8; border-radius:14px; }
[data-testid="stFileUploaderDropzone"] { background:#f8faff; }
[data-testid="stFileUploaderDropzone"] * { color:#26344d !important; }
[data-testid="stSelectbox"] [role="combobox"] { color:#172033 !important; background:#fff !important; }
[data-testid="stExpander"] { background:#fff; border:1px solid #e2e8f0; border-radius:12px; }
.stButton button, [data-testid="stButton"] button,
[data-testid="stBaseButton-primary"] {
  background:#315bea !important; border:1px solid #315bea !important;
  color:#fff !important;
}
.stButton button *, [data-testid="stButton"] button *,
[data-testid="stBaseButton-primary"] * { color:#fff !important; }
.stButton button:disabled, [data-testid="stButton"] button:disabled {
  background:#9aa8c2 !important; border-color:#9aa8c2 !important; color:#fff !important;
}
[data-testid="stFileUploader"] button {
  background:#ffffff !important; border:1px solid #94a3b8 !important;
  color:#172033 !important; opacity:1 !important;
}
[data-testid="stFileUploader"] button * { color:#172033 !important; }
[data-testid="stAlert"] { background:#fff !important; color:#172033 !important; border:1px solid #d5deeb !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span { color:#172033 !important; }
[data-testid="stAlert"] svg { fill:currentColor; }
[data-testid="stDataFrame"] { background:#fff; }
code { color:#173ea5 !important; background:#edf2ff !important; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Document Intelligence")
st.caption("Upload a document to automatically extract its text and generate a summary, category, keywords, and entities.")

docs = list_documents()
a, b, c = st.columns(3)
a.metric("Documents", len(docs))
b.metric("Analyzed", sum(d["status"] == "Processed" for d in docs))
c.metric("Waiting for analysis", sum(d["status"] == "Uploaded" for d in docs))

st.subheader("Upload and analyze a document")
upload = st.file_uploader("Choose PDF, TXT, JPG, or PNG", type=["pdf", "txt", "jpg", "jpeg", "png"],
                          help=f"Maximum file size: {MAX_FILE_SIZE // (1024 * 1024)} MB")
if st.button("⬆️  Upload and analyze", type="primary", disabled=upload is None):
    try:
        extracted_text, file_type = process_uploaded_file(upload.name, upload.getvalue())
        with st.spinner("Extracting text and running document analysis…"):
            result = analyze_document(extracted_text)
            doc_id = save_document(upload.name, file_type, extracted_text, result)
        st.session_state["selected_document_id"] = doc_id
        st.success(f"{upload.name} uploaded and analyzed successfully. Results are shown below.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Could not upload this file: {exc}")

st.divider()
st.subheader("2. Uploaded documents")
docs = list_documents()
if not docs:
    st.info("Your uploaded documents and their summaries will appear in this table.")
else:
    table_rows = []
    for d in docs:
        overview = d["summary"] if d["summary"] else "Not analyzed yet — select the document and run analysis."
        overview = overview.split("**Key points**", 1)[0]
        overview = re.sub(r"\*\*Overview\*\*|[\n*]+", " ", overview).strip()
        if len(overview) > 150:
            overview = overview[:147].rsplit(" ", 1)[0] + "…"
        table_rows.append({
            "File name": d["filename"], "Uploaded": d["uploaded_at"].replace("T", " ").replace("+00:00", " UTC"),
            "Status": d["status"], "Category": d["category"] or "—", "Short overview": overview,
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    labels = {f"{d['filename']} · {d['status']} · {d['uploaded_at'][:16]}": d["id"] for d in docs}
    current_id = st.session_state.get("selected_document_id")
    default_index = next((i for i, value in enumerate(labels.values()) if value == current_id), 0)
    selected_label = st.selectbox("Select a document to analyze or view", list(labels), index=default_index)
    doc_id = labels[selected_label]
    doc = get_document(doc_id)

    col_analyze, col_delete, _ = st.columns([1.5, 1, 4])
    with col_analyze:
        button_text = "✨  Analyze document" if doc["status"] != "Processed" else "↻  Analyze again"
        if st.button(button_text, type="primary", use_container_width=True):
            with st.spinner("Analyzing document…"):
                result = analyze_document(doc["text"])
                complete_document(doc_id, result)
            st.session_state["selected_document_id"] = doc_id
            st.success("Analysis complete.")
            st.rerun()
    with col_delete:
        if st.button("Delete", use_container_width=True):
            delete_document(doc_id)
            st.session_state.pop("selected_document_id", None)
            st.rerun()

    doc = get_document(doc_id)
    if doc["status"] == "Uploaded":
        st.info("This document is uploaded and ready. Click **Analyze document** to generate its overview, category, keywords, and entities.")
    else:
        st.subheader(f"Analysis: {doc['filename']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Category", doc["category"])
        m2.metric("Words", doc["word_count"])
        m3.metric("Entities found", len(doc["entities"]))
        left, right = st.columns([1.2, 1])
        with left:
            st.markdown("#### Document summary")
            st.markdown(doc["summary"] or "No summary could be generated.")
            st.markdown("#### Keywords")
            if doc["keywords"]:
                st.write("  ·  ".join(f"`{word}`" for word in doc["keywords"]))
            else:
                st.write("No keywords detected.")
        with right:
            st.markdown("#### Named entities")
            if doc["entities"]:
                st.dataframe(pd.DataFrame(doc["entities"]), use_container_width=True, hide_index=True)
            else:
                st.write("No entities detected.")
        with st.expander("View extracted text"):
            st.text(doc["text"] or "No text extracted.")

with st.expander("About the analysis"):
    st.write("This simple demo classifies documents with transparent keyword rules, selects representative sentences for the summary, ranks frequent words as keywords, and detects entities with text patterns. It runs locally without model downloads or API keys; review results for important documents.")
