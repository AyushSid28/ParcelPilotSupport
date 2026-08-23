from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
ROOT = BACKEND_DIR.parent
SOURCE_DIR = ROOT / "data" / "source"
DB_PATH = ROOT / "data" / "parcelpilot.db"
WEB_DIST = ROOT / "web" / "dist"
STATIC_DIR = APP_DIR / "static"
