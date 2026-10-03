#!/usr/bin/env python3
"""Create a test-only Yamlr entitlement using the committed test key pair."""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path

import jwt


TEST_PRIVATE_KEY = (
    Path(__file__).resolve().parent.parent
    / "native_core"
    / "tests"
    / "fixtures"
    / "licensing_test_private.pem"
)


def generate_dummy_key(_legacy_machine_id: str = "") -> str:
    """Return a fixture-signed entitlement that production keys cannot verify."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "license_version": 1,
        "sub": "org_yamlr_test",
        "tier": "enterprise",
        "org_id": "org_yamlr_test",
        "seats": 1,
        "iss": "yamlr-entitlement",
        "aud": "yamlr",
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(days=1)).timestamp()),
    }
    private_key = TEST_PRIVATE_KEY.read_text(encoding="utf-8")
    return jwt.encode(payload, private_key, algorithm="RS256")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "machine_id",
        nargs="?",
        default="",
        help="Deprecated compatibility argument; test entitlements are not machine-bound",
    )
    args = parser.parse_args()

    try:
        token = generate_dummy_key(args.machine_id)
    except OSError as error:
        parser.error(f"Cannot read the dedicated test signing key: {error}")

    print("TEST ONLY: this token is signed with the committed test key.")
    print("It cannot be verified by a production Yamlr installation.\n")
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
