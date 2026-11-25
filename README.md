# Document Intelligence (Streamlit)

A small local app for uploading PDF, TXT, JPG, and PNG documents, extracting text, classifying the document, producing keywords and a short summary, and finding basic entities. Results and metadata are stored in local `documents.db` (SQLite).

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501.

For image OCR, also install the Tesseract OCR engine. On macOS: `brew install tesseract`. On Debian/Ubuntu: `sudo apt install tesseract-ocr`. PDF extraction works for text PDFs; scanned PDFs need OCR conversion first. Maximum upload size is 10 MB.

## Workflow

Upload and validate extension/size/content → extract PDF/TXT/OCR text → normalize whitespace → classify and analyze → save text and results to SQLite → view, inspect, or delete documents in the UI.

The NLP is deliberately rule based and lightweight so the project runs without model downloads or API keys. Classification uses document vocabulary, keywords use word frequency, summaries select representative sentences, and entity detection uses patterns. This is explainable but less accurate than trained NLP models, and the capitalized-name detector does not reliably distinguish people from organizations.
