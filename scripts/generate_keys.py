#!/usr/bin/env python3
"""Generate a Yamlr signing key pair outside the source checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def generate_keys(output_dir: Path) -> tuple[Path, Path]:
    destination = output_dir.expanduser().resolve()
    try:
        destination.relative_to(REPOSITORY_ROOT)
    except ValueError:
        pass
    else:
        raise ValueError(
            "Signing keys must be generated outside the Yamlr source checkout."
        )

    private_key_path = destination / "private_key.pem"
    public_key_path = destination / "public_key.pem"
    if private_key_path.exists() or public_key_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite an existing key pair in '{destination}'."
        )

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    destination.mkdir(parents=True, exist_ok=True)
    private_fd = os.open(
        private_key_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(private_fd, "wb") as private_file:
            private_file.write(private_bytes)
        with public_key_path.open("xb") as public_file:
            public_file.write(public_bytes)
    except OSError:
        private_key_path.unlink(missing_ok=True)
        raise

    return private_key_path, public_key_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory outside the repository for the new private/public key pair",
    )
    args = parser.parse_args()

    try:
        private_path, public_path = generate_keys(args.output_dir)
    except (FileExistsError, OSError, ValueError) as error:
        parser.error(str(error))

    print("Signing key pair generated outside the source checkout.")
    print(f"Private key: {private_path}")
    print(f"Public key:  {public_path}")
    print("Protect the private key and keep it out of source control and release artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
