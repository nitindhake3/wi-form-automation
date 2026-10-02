import base64
import json
import sys
from pathlib import Path

def main():
    auth_path = Path("auth.json")
    if not auth_path.exists():
        print("[ERROR] auth.json not found! Please run 'python main.py --setup-auth' first to log into your Google Account.")
        sys.exit(1)

    with open(auth_path, "rb") as f:
        raw_bytes = f.read()

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
        cookie_count = len(data.get("cookies", []))
        if cookie_count == 0:
            print("[WARNING] auth.json contains 0 cookies. Make sure you were fully logged in before pressing ENTER!")
        else:
            print(f"[INFO] Successfully loaded local auth.json with {cookie_count} saved session cookies.")
    except Exception as e:
        print(f"[ERROR] Local auth.json is invalid JSON: {e}")
        sys.exit(1)

    b64_encoded = base64.b64encode(raw_bytes).decode("utf-8")

    print("\n" + "=" * 70)
    print("COPY THE SINGLE-LINE BASE64 SECRET BELOW AND PASTE IT INTO GITHUB SECRET 'AUTH_JSON':")
    print("=" * 70)
    print(b64_encoded)
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
