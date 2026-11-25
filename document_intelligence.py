import io
import re
from collections import Counter

MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_TYPES = {"pdf", "txt", "jpg", "jpeg", "png"}
STOP_WORDS = set("a an and are as at be by for from has have in into is it its of on or that the their this to was were will with your you we our document information following about which there when where who what how can may not all any also such more than then them they he she his her i me my date amount total please regards dear subject page invoice resume agreement report general".split())


def process_uploaded_file(filename, data):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_TYPES:
        raise ValueError("Unsupported file type. Upload PDF, TXT, JPG, or PNG.")
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_FILE_SIZE:
        raise ValueError("File is larger than the 10 MB limit.")
    try:
        if ext == "txt":
            text = data.decode("utf-8-sig", errors="replace")
        elif ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(data))
            image.verify()
            image = Image.open(io.BytesIO(data)).convert("RGB")
            text = pytesseract.image_to_string(image)
    except ImportError as exc:
        if ext in {"jpg", "jpeg", "png"}:
            raise ValueError("OCR dependencies are missing. Install requirements and Tesseract OCR (see README).") from exc
        raise ValueError("PDF reader dependency is missing. Install requirements.txt.") from exc
    except NameError as exc:
        if ext == "pdf" and "xrange" in str(exc):
            raise ValueError("PDF support is blocked by an outdated PyCrypto package. Run `python3 -m pip install --upgrade pycryptodome` and restart the app.") from exc
        raise ValueError(f"This file could not be read: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"This file is corrupted or unreadable: {exc}") from exc
    text = normalize_text(text)
    if not text:
        raise ValueError("No readable text was found. The PDF may be scanned; image OCR supports JPG/PNG.")
    return text, ext


def normalize_text(text):
    text = text.replace("\x00", " ").replace("\r", "\n")
    # PDF extractors often insert a line break at the visual edge of each line,
    # even when a sentence continues. Join those wrapped lines before analysis.
    text = re.sub(r"(?<=[A-Za-z0-9,;])[ \t]*\n(?=[a-z(])", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def analyze_document(text):
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    counts = Counter(w for w in words if w not in STOP_WORDS)
    keywords = [w for w, _ in counts.most_common(8)]
    category = classify_document(text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 20]
    summary = summarize(sentences, counts)
    entities = extract_entities(text)
    return {"category": category, "keywords": keywords, "summary": summary, "entities": entities, "word_count": len(re.findall(r"\b\w+\b", text))}


def classify_document(text):
    t = text.lower()
    rules = {
        "Invoice": ["invoice", "amount due", "bill to", "subtotal", "tax", "payment due"],
        "Resume": ["resume", "curriculum vitae", "experience", "education", "skills", "employment"],
        "Agreement": ["agreement", "whereas", "hereby", "parties", "terms and conditions", "contract"],
        "Report": ["executive summary", "methodology", "findings", "conclusion", "annual report", "results"],
    }
    scores = {label: sum(t.count(term) for term in terms) for label, terms in rules.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "General Document"


def summarize(sentences, counts):
    if not sentences:
        return "No summary could be generated from the extracted text."
    def score_sentence(item):
        index, sentence = item
        words = re.findall(r"[A-Za-z'-]{3,}", sentence.lower())
        term_score = sum(counts[word] for word in words) / max(len(words) ** 0.5, 1)
        fact_score = 1.5 if re.search(r"\d|\$|€|£|₹|%", sentence) else 0
        position_score = max(0, 1.2 - index * 0.12)
        return term_score + fact_score + position_score

    # Keep up to five useful sentences, retaining their original document order.
    selected = sorted(sorted(enumerate(sentences), key=score_sentence, reverse=True)[:5])
    lead = selected[0][1]
    key_points = [sentence for _, sentence in selected[1:]]
    summary = f"**Overview**\n\n{lead}"
    if key_points:
        summary += "\n\n**Key points**\n\n" + "\n".join(f"- {sentence}" for sentence in key_points)
    return summary[:1800] + ("…" if len(summary) > 1800 else "")


def extract_entities(text):
    found = []
    patterns = [
        ("Email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        ("Money", r"(?:\$|€|£|₹|USD\s?|INR\s?)\s?\d[\d,]*(?:\.\d{1,2})?\b"),
        ("Date", r"\b(?:\d{1,2}[/-]\d{1,2}[/-](?:\d{2,4})|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b"),
        ("Person / Organization", r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b"),
    ]
    seen = set()
    for label, pattern in patterns:
        for match in re.findall(pattern, text):
            key = (label, match)
            if key not in seen:
                found.append({"type": label, "value": match})
                seen.add(key)
    return found[:100]
