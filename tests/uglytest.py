from app.parsers.booking import parse_email
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # directory containing uglytest.py
fixture_path = BASE_DIR / "fixtures" / "hub_premier_inn_test.eml"

with open(fixture_path, "rb") as f:
    raw_bytes = f.read()

parsed = parse_email(raw_bytes)
print(parsed)