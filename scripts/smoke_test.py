import sys
import os

# Add backend root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Importing src.core.config...")
    from src.core import config
    print("✅ src.core.config imported")

    print("Importing src.api.routes...")
    from src.api import routes
    print("✅ src.api.routes imported")

    print("Importing src.pipeline.complete_verifier...")
    from src.pipeline.complete_verifier import CompleteCertificateVerifier
    print("✅ src.pipeline.complete_verifier imported")

    print("Importing src.agents.ocr.triple_ocr...")
    from src.agents.ocr.triple_ocr import TripleOCR
    print("✅ src.agents.ocr.triple_ocr imported")

    print("ALL IMPORTS SUCCESSFUL")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
