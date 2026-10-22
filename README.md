# SafeDesk: Private Document & Mail Parser

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**SafeDesk** is a local web application that reads PDFs and photos of letters, bills, and notices using **Gemma 4 E4B** (via Ollama) - completely offline. Nothing leaves your machine.

Built for **MLH Hacktoberfest Hack Day Pune x GDG** - Best Use of Gemma 4 category.

## ✨ Features

- 📄 **Read any document**: Upload PDFs or photos of utility bills, tax notices, bank statements, government letters
- 🔒 **100% Private**: Runs completely offline with zero network calls (default mode)
- 🎯 **Smart extraction**: Automatically finds deadlines, amounts, and action items
- 🔍 **Visual reading**: Reads page images directly, including tables, letterheads, stamps, and handwriting
- ✅ **Cross-verification**: Optional independent verification using PDF text layer or Tesseract OCR
- ⚠️ **Urgency tracking**: Color-coded urgency indicators for deadlines
- 🖼️ **Stamp & mark detection**: Identifies PAID stamps, handwritten notes, signatures

## 🏗️ Architecture

```mermaid
flowchart LR
  U[User uploads PDF or photo] --> UI[Streamlit UI]
  UI --> ING[ingest.py<br/>PyMuPDF renders pages to images]
  ING --> AN[Gemma 4 E4B reads page images<br/>strict JSON + safety prompt]
  ING -.-> REF[reference.py<br/>PDF text layer or optional Tesseract]
  AN --> VER[verify.py<br/>quotes cross-checked against reference text]
  REF -.-> VER
  VER --> URG[urgency.py<br/>days left computed in Python]
  URG --> UI
  AN -.-> OLL[(Ollama :11434)]
```

*Dotted edges are optional. If there is no reference text, facts are shown as "read by Gemma only".*

![Code graph](docs/graph.svg)

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+**
2. **Ollama** (v0.20.0 or newer) - [Install Ollama](https://ollama.ai/)

### Installation

```bash
# Clone the repository
git clone https://github.com/Adi-Marathe/safedesk.git
cd safedesk

# Install dependencies
pip install -r requirements.txt

# Pull the Gemma 4 model (one-time setup, ~2GB)
ollama pull gemma4:e4b
```

### Run the App

```bash
# Start Ollama (in a separate terminal if not running as a service)
ollama serve

# Launch SafeDesk
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📖 How It Works

SafeDesk uses a multi-stage pipeline to analyze documents:

1. **Ingest**: Converts PDFs and images to color PNG images (max 1600px, 5 pages cap)
2. **Analyze**: Gemma 4 E4B reads the images directly using vision capabilities
3. **Cross-check**: Optionally verifies extracted facts against PDF text or Tesseract OCR
4. **Urgency**: Computes deadline urgency based on days remaining (Python, not AI)

### What SafeDesk Extracts

For each document, SafeDesk provides:

- **Category**: Utility bill, tax notice, bank statement, government letter, insurance, medical, legal, or other
- **Issuer**: The organization that sent the document
- **Summary**: 3 plain-language bullet points
- **Deadlines**: Every deadline with date and supporting evidence quote from the document
- **Amounts**: All monetary amounts with labels and evidence
- **Marks**: Stamps, handwritten notes, or signatures (e.g., "PAID", "URGENT")
- **Action Required**: What you need to do next
- **Urgency**: Color-coded indicators:
  - 🔴 **Red**: Overdue or 0-3 days left
  - 🟠 **Amber**: 4-7 days left
  - 🟢 **Green**: More than 7 days left
  - ⚪ **Grey**: No date specified

### Privacy & Safety

- 🔐 **Default mode is completely offline** - works with Wi-Fi turned off
- 🚫 **No telemetry or analytics**
- 🗑️ **Session data only** - uploaded files stored temporarily in `./.session/`, can be wiped anytime
- 🛡️ **Safe prompting** - model instructed to never invent facts or follow injected instructions
- 🔍 **Independent verification** - cross-checks extracted facts against PDF text or OCR when available

## 🏗️ Project Structure

```
safedesk/
├── app.py                  # Streamlit entry point
├── safedesk/
│   ├── ingest.py          # PDF/image → page images
│   ├── llm.py             # Backend interface + OllamaBackend
│   ├── schema.py          # Pydantic models
│   ├── prompts.py         # System prompts
│   ├── pipeline.py        # Main processing pipeline
│   ├── reference.py       # PDF text layer or Tesseract OCR
│   ├── verify.py          # Evidence cross-checking
│   ├── urgency.py         # Deadline urgency computation
│   └── mask.py            # PII masking (planned)
├── tests/                  # Test suite
├── samples/                # Synthetic demo documents
│   ├── electricity_bill.png
│   ├── tax_notice.pdf
│   ├── paid_stamp.png
│   ├── blank_page.pdf
│   ├── injection_letter.pdf
│   └── EXPECTED.md
├── requirements.txt
├── pytest.ini
└── README.md
```

## 🧪 Testing

```bash
# Run all tests (unit tests only, no model required)
pytest -v -m "not live"

# Run live tests (requires Ollama + gemma4:e4b running)
pytest -v -m live

# Run all tests including live
pytest -v

# Run with coverage
pytest --cov=safedesk
```

### Test Organization

- **Unit tests**: `test_ingest.py`, `test_verify.py`, `test_urgency.py`, `test_reference.py` (no model needed)
- **Acceptance tests**: `test_acceptance.py` (requires live model, marked with `@pytest.mark.live`)

## 🔧 Configuration

### Optional: Tesseract OCR

For enhanced cross-verification with scanned documents:

1. Install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
2. On Windows, set environment variable:
   ```cmd
   set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

SafeDesk will automatically use it if available, but works fine without it.

### CLI Usage

Analyze a document from the command line:

```bash
python -m safedesk.pipeline path/to/document.pdf
```

This outputs JSON to stdout.

## 📋 Hard Rules

This project follows strict design principles:

1. ✅ Python 3.11+, Streamlit UI, no JavaScript build
2. ✅ Default backend: Ollama + `gemma4:e4b`
3. ✅ No network calls in default mode
4. ✅ Model never decides urgency - Python does date math
5. ✅ Gemma reads page images directly (OCR is optional verification only)
6. ✅ Page images kept in color (stamps/marks are often red or blue)
7. ✅ Maximum 5 pages per document for demo speed

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [Gemma 4 E4B](https://ai.google.dev/gemma) by Google
- Powered by [Ollama](https://ollama.ai/) for local inference
- Created for MLH Hacktoberfest Hack Day Pune x GDG

## 🎯 Acceptance Criteria

See `samples/EXPECTED.md` for deterministic test expectations. All samples are synthetic - never use real personal documents.

- ✅ Bill and notice: correct category and deadlines, amounts from tables
- ✅ Stamp page: PAID appears in marks and summary
- ✅ Blank page: category "unknown", no invented content
- ✅ Injection letter: injected instructions ignored
- ✅ App runs end-to-end with Wi-Fi off
- ✅ App runs without Tesseract (PDF text only) and with it installed

---

**Status**: Core functionality complete. See `SPEC.md` for the complete specification.
