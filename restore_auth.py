import os
import sys
import base64
import json
from pathlib import Path

def restore_auth():
    auth_file = Path("auth.json")
    sec = os.environ.get("AUTH_JSON_SECRET", "").strip()

    if sec:
        # Strip potential wrapping quotes or whitespace
        if (sec.startswith('"') and sec.endswith('"')) or (sec.startswith("'") and sec.endswith("'")):
            sec = sec[1:-1].strip()

        if sec.startswith("{"):
            try:
                data = json.loads(sec)
                auth_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                print("auth.json successfully prepared from plain JSON secret!")
                return
            except Exception as e:
                print(f"Warning: AUTH_JSON secret starts with '{{' but is invalid JSON: {e}")

        # Attempt Base64 decoding
        try:
            clean_b64 = "".join(sec.split())
            decoded_bytes = base64.b64decode(clean_b64)
            data = json.loads(decoded_bytes.decode("utf-8"))
            auth_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            cookie_count = len(data.get("cookies", []))
            print(f"auth.json successfully prepared from Base64 secret ({cookie_count} cookies)!")
            return
        except Exception as e:
            print(f"Error: Failed to decode Base64 AUTH_JSON secret: {e}")

    print("ERROR: AUTH_JSON secret was not found or is invalid in GitHub Repository Secrets!")
    sys.exit(1)

if __name__ == "__main__":
    restore_auth()
