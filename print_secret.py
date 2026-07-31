import json
from pathlib import Path

auth_path = Path("auth.json")
if not auth_path.exists():
    print("Error: auth.json not found! Run 'python main.py --setup-auth' first.")
else:
    with open(auth_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    print("=" * 70)
    print("COPY ALL THE TEXT BELOW AND PASTE IT INTO GITHUB SECRET 'AUTH_JSON':")
    print("=" * 70)
    print(content)
    print("=" * 70)
