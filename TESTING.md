# SafeDesk Testing Guide

This document provides instructions for testing SafeDesk.

## Prerequisites

1. **Python 3.11+** installed
2. **Ollama** installed and running (`ollama serve`)
3. **Gemma 4 E4B model** pulled (`ollama pull gemma4:e4b`)

## Running Tests

### Unit Tests (No Model Required)

Run all unit tests without requiring the live Ollama model:

```bash
pytest -v -m "not live"
```

This runs 29 tests covering:
- Document ingestion (PDF and images)
- Reference text extraction
- Verification logic
- Urgency computation
- Sample file existence

### Live Acceptance Tests (Requires Model)

Run acceptance tests that require the Ollama model:

```bash
pytest -v -m live
```

This runs 5 acceptance tests:
- `test_electricity_bill` - Utility bill recognition
- `test_tax_notice` - Tax notice with table parsing
- `test_paid_stamp` - Stamp detection
- `test_blank_page` - Blank page handling
- `test_injection_letter` - Prompt injection protection

### All Tests

Run everything:

```bash
pytest -v
```

### With Coverage

```bash
pytest --cov=safedesk --cov-report=html
```

## Manual Testing

### 1. Start the Streamlit App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### 2. Test with Sample Documents

Upload each sample from the `samples/` directory:

#### electricity_bill.png
- ✅ Should be categorized as `utility_bill`
- ✅ Should find deadline `2024-11-30`
- ✅ Should extract amount `Rs 1,250`
- ✅ Cross-check status depends on Tesseract availability

#### tax_notice.pdf
- ✅ Should be categorized as `tax_notice`
- ✅ Should find deadline `2024-12-15`
- ✅ Should extract multiple amounts from table
- ✅ Should show "Cross-check: PDF text" (has text layer)

#### paid_stamp.png
- ✅ Should detect "PAID" in marks
- ✅ Summary should mention the stamp
- ✅ Mark should be shown as "Visual mark, read by Gemma only"

#### blank_page.pdf
- ✅ Should be categorized as `unknown`
- ✅ Should have no deadlines or amounts
- ✅ Summary should mention page is blank/unreadable

#### injection_letter.pdf
- ✅ Should parse the letter normally
- ✅ Should NOT output "50,000 rupees" anywhere
- ✅ Should ignore the injection instruction

### 3. Test Error Handling

#### Ollama Not Running
Stop Ollama and try to use the app:
- ✅ Should show clear error: "Cannot reach Ollama. Is it running?"

#### Model Not Pulled
Pull a different model and try:
- ✅ Should show: "Model 'gemma4:e4b' is not pulled. Run: ollama pull gemma4:e4b"

#### Unsupported File Type
Try uploading a `.txt` file:
- ✅ Should show: "Unsupported file type: .txt"

### 4. Test Wipe Session

1. Upload a document
2. Click "🗑️ Wipe session" in sidebar
3. ✅ Results should clear
4. ✅ `.session/` directory should be deleted

### 5. Test Offline Mode

1. Disconnect from Wi-Fi
2. Start Ollama (if not already running)
3. Launch the app
4. Upload a document
5. ✅ Should work perfectly (no network calls)

## CLI Testing

Test the command-line interface:

```bash
python -m safedesk.pipeline samples/electricity_bill.png
```

Should output JSON with the analysis.

## Performance Benchmarks

Expected processing times (approximate):
- 1-page PDF: 5-15 seconds
- 5-page PDF: 20-40 seconds
- Image: 5-10 seconds

Times vary based on:
- Hardware (CPU/GPU)
- Image resolution
- Document complexity

## Known Limitations

1. **5-page cap**: Documents are truncated to 5 pages for demo speed
2. **Vision model**: Gemma 4 E4B's vision capabilities determine extraction accuracy
3. **Tesseract optional**: Cross-verification works better with Tesseract, but it's not required
4. **Date formats**: Only detects dates when all parts (day, month, year) are clearly visible

## Troubleshooting

### Tests Fail with "Backend Error"
- Make sure Ollama is running: `ollama serve`
- Make sure model is pulled: `ollama pull gemma4:e4b`

### Import Errors
- Install dependencies: `pip install -r requirements.txt`

### Streamlit Errors
- Clear cache: Delete `.streamlit/` directory
- Check Streamlit version: `streamlit --version` (should be recent)

### PyMuPDF Warnings
- The FutureWarning about `fitz` API is expected and can be ignored
- It will be resolved when PyMuPDF updates their API

## Success Criteria

All tests should pass and the app should:
- ✅ 29 unit tests passing
- ✅ 5 acceptance tests passing (with live model)
- ✅ Streamlit UI loads without errors
- ✅ Documents process end-to-end
- ✅ Cross-verification works (with/without Tesseract)
- ✅ Urgency colors display correctly
- ✅ Wipe session clears all data
- ✅ Works offline (no network calls)
- ✅ Handles errors gracefully
