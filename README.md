# Certificate Verification Backend

This system creates a secure, AI-powered pipeline to verify certificates from major e-learning platforms (Udemy, Coursera, etc.).

## 🚀 Key Features

- **Triple OCR Engine**: uses EasyOCR, Tesseract, and Mistral AI for high-accuracy text extraction.
- **Forensic Analysis**: Mistral Vision analysis to detect image manipulation.
- **Verification Agents**: Automated verification against trusted domains.
- **History Tracking**: SQLite database to store verification results.

## 📁 Project Structure

The project has been refactored into a modular `src` architecture:

```
backend/
├── src/
│   ├── agents/         # AI Agents (OCR, Forensics, Verification)
│   ├── api/            # FastAPI Routes and App
│   ├── core/           # Config and Models
│   ├── database/       # Database Interaction
│   └── pipeline/       # Main Verification Logic
├── scripts/            # Helper scripts (verify_certificate.py)
├── tests/              # Automated tests
└── data/               # Data storage (DB, images)
```

## 🛠️ How to Run

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Server**
   ```bash
   uvicorn src.api.main:app --reload
   ```

3. **Run Manual Verification**
   ```bash
   python scripts/verify_certificate.py data/sample_cert.jpg
   ```

## 🧠 "Stuff" Folder (Conceptual)

The `stuff/` folder contains conceptual documents used during the design phase:

### 1. Flow (`stuff/flow`)
Describes the high-level logic pipeline:
`Input → Normalization → OCR (Parallel) → Mistral Reasoning → Verification → Verdict`

### 2. Structure (`stuff/structure`)
Describes the intended module layout (which matches the current `src/` implementation).

---
*Built with FastAPI, Mistral AI, and PaddleOCR.*
