import base64
import datetime as dt
import json
import re
from pathlib import Path


def _b64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * ((4 - (len(s) % 4)) % 4)
    return base64.b64decode(s)


def main() -> int:
    path = Path("config/services_matrix.yaml")
    txt = path.read_text(encoding="utf-8")

    m = re.search(r'(?m)^\s*env_var:\s*"([^"]+)"\s*$', txt)
    if not m:
        raise SystemExit("env_var not found in config/services_matrix.yaml")

    token = m.group(1)
    parts = token.split(".")
    if len(parts) != 3:
        raise SystemExit("env_var is not a 3-part JWT")

    payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    iat = payload.get("iat")
    exp = payload.get("exp")

    def to_local(unix_s: int) -> dt.datetime:
        return dt.datetime.fromtimestamp(int(unix_s), tz=dt.timezone.utc).astimezone()

    now = dt.datetime.now().astimezone()

    print(f"iat_local = {to_local(iat) if iat else None}")
    print(f"exp_local = {to_local(exp) if exp else None}")
    print(f"now_local = {now}")
    if exp:
        print(f"expired  = {now > to_local(exp)}")
    else:
        print("expired  = unknown (no 'exp' claim in token)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
