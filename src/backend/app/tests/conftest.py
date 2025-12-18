import sys
from pathlib import Path

# Ensure the backend package is on the import path for tests
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
