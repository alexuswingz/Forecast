import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config

print("USE_SQLITE:", Config.USE_SQLITE)
print("DATABASE_URL:", Config.DATABASE_URL)



