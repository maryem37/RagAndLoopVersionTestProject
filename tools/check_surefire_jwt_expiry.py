"""Check whether the JWT used during Maven Surefire tests is expired.

- Reads the most recent Surefire XML report that contains a TEST_JWT_TOKEN property.
- Decodes JWT payload (no signature verification) and prints exp/sub/ttl/expired.
- Does NOT print the token.

Usage:
  python tools/check_surefire_jwt_expiry.py

Exit codes:
  0: script ran (token may or may not be found)
  2: invalid JWT format or payload decode error
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SUREFIRE_DIR_CANDIDATES = [
    Path("output/tests/target/surefire-reports"),
    Path("target/surefire-reports"),
]


@dataclass(frozen=True)
class JwtExpiryInfo:
    source_report: str
    jwt_found: bool
    jwt_format_ok: bool
    sub: Optional[str]
    exp_utc: Optional[str]
    ttl_seconds: Optional[int]
    expired: Optional[bool]


def _urlsafe_b64decode_nopad(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _extract_token_from_surefire_xml(xml_text: str) -> Optional[str]:
    # Surefire writes properties like:
    # <property name="TEST_JWT_TOKEN" value="eyJ..."/>
    match = re.search(
        r'<property\s+name="TEST_JWT_TOKEN"\s+value="([^"]+)"\s*/>',
        xml_text,
    )
    if not match:
        return None
    return match.group(1).strip()


def _find_latest_report_with_token() -> tuple[Optional[Path], Optional[str]]:
    reports: list[Path] = []
    for base in SUREFIRE_DIR_CANDIDATES:
        if base.is_dir():
            reports.extend(base.glob("TEST-*.xml"))

    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for report_path in reports:
        try:
            xml = report_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        token = _extract_token_from_surefire_xml(xml)
        if token:
            return report_path, token

    return None, None


def _decode_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("JWT must have 3 parts")
    payload_bytes = _urlsafe_b64decode_nopad(parts[1])
    return json.loads(payload_bytes.decode("utf-8"))


def get_jwt_expiry_info() -> JwtExpiryInfo:
    report_path, token = _find_latest_report_with_token()
    if not token or not report_path:
        return JwtExpiryInfo(
            source_report=str(report_path.as_posix()) if report_path else "",
            jwt_found=False,
            jwt_format_ok=False,
            sub=None,
            exp_utc=None,
            ttl_seconds=None,
            expired=None,
        )

    parts = token.split(".")
    jwt_format_ok = len(parts) == 3
    if not jwt_format_ok:
        return JwtExpiryInfo(
            source_report=report_path.as_posix(),
            jwt_found=True,
            jwt_format_ok=False,
            sub=None,
            exp_utc=None,
            ttl_seconds=None,
            expired=None,
        )

    payload = _decode_payload(token)

    sub = payload.get("sub")
    sub_str = str(sub) if sub is not None else None

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        now = datetime.now(timezone.utc)
        exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
        ttl_seconds = int(exp_dt.timestamp() - now.timestamp())
        return JwtExpiryInfo(
            source_report=report_path.as_posix(),
            jwt_found=True,
            jwt_format_ok=True,
            sub=sub_str,
            exp_utc=exp_dt.isoformat(),
            ttl_seconds=ttl_seconds,
            expired=ttl_seconds <= 0,
        )

    return JwtExpiryInfo(
        source_report=report_path.as_posix(),
        jwt_found=True,
        jwt_format_ok=True,
        sub=sub_str,
        exp_utc=None,
        ttl_seconds=None,
        expired=None,
    )


def main() -> int:
    info = get_jwt_expiry_info()

    print(f"source_report: {info.source_report or None}")
    print(f"jwt_found: {info.jwt_found}")
    print(f"jwt_format_ok: {info.jwt_format_ok}")
    print(f"sub: {info.sub!r}")
    print(f"exp_utc: {info.exp_utc or 'unknown'}")
    print(f"ttl_seconds: {info.ttl_seconds if info.ttl_seconds is not None else 'unknown'}")
    print(f"expired: {info.expired if info.expired is not None else 'unknown'}")

    if info.jwt_found and not info.jwt_format_ok:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
