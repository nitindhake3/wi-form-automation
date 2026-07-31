import base64
import json
from pathlib import Path

auth_path = Path("auth.json")
if not auth_path.exists():
    print("Error: auth.json not found! Run 'python main.py --setup-auth' first.")
else:
    with open(auth_path, "rb") as f:
        raw_bytes = f.read()

    # Verify local auth.json is valid JSON
    try:
        json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Error: Local auth.json is invalid JSON: {e}")
        exit(1)

    b64_encoded = base64.b64encode(raw_bytes).decode("utf-8")

    print("=" * 70)
    print("COPY THE SINGLE-LINE BASE64 SECRET BELOW AND PASTE IT INTO GITHUB SECRET 'AUTH_JSON':")
    print("=" * 70)
    print(b64_encoded)
    print("=" * 70)
