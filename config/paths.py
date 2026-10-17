from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
DATA_DIR = PROJECT_ROOT / "data"

CLUBS_FILE = DATA_DIR / "clubs.json"
MANIFEST_FILE = DATA_DIR / "manifest.json"
RESULTS_FILE = DATA_DIR / "results.csv"
