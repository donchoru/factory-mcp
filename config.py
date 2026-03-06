import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "factory.db"

# DB 설정 — DB_TYPE=oracle 로 전환 가능
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
ORACLE_DSN = os.getenv("ORACLE_DSN", "")
ORACLE_USER = os.getenv("ORACLE_USER", "")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")
