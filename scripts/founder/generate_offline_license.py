import datetime
import json
import os
import re
import sys
import jwt
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Internal utility for generating offline license bundles
# Issues cryptographically signed licenses for enterprise customers in air-gapped environments.

# PRIVATE KEY (KEEP SECRET)
# Loaded explicitly from YAMLR_FOUNDER_KEY or YAMLR_PRIVATE_KEY.

def _private_key_from_environment(environ: dict[str, str] | None = None) -> str:
    """Return an explicitly configured signing key without probing the source tree."""
    environment = os.environ if environ is None else environ
    private_key = environment.get("YAMLR_FOUNDER_KEY") or environment.get("YAMLR_PRIVATE_KEY")
    if not private_key or not private_key.strip():
        raise ValueError(
            "YAMLR_FOUNDER_KEY or YAMLR_PRIVATE_KEY is required; "
            "the generator does not load signing keys from the repository."
        )
    return private_key

def generate_license(
    machine_id: str,
    customer: str,
    tier: str = "TEAM",
    days: int = 365,
    organization_id: str | None = None,
    seats: int | None = None,
    nodes: int | None = None,
):
    """
    Generates a signed JWS token for an offline license using RS256.
    """
    # Kept as an ignored compatibility argument; current licenses follow users or organizations.
    customer = customer.strip()
    tier = tier.strip().lower()
    if tier == "pro":
        tier = "team"
    if not customer:
        raise ValueError("Customer name must not be empty")
    if tier not in {"team", "enterprise"}:
        raise ValueError("Tier must be team or enterprise")
    if days <= 0:
        raise ValueError("License duration must be greater than zero days")

    organization_id = (organization_id or customer).strip()
    if not organization_id:
        raise ValueError("Organization ID must not be empty")
    if tier == "team" and seats is None:
        seats = 1
    if tier == "team" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", customer):
        raise ValueError("Team license customer must be the named developer's email address")
    if tier == "team" and (seats is None or seats < 1):
        raise ValueError("Team organization seat count must be at least one")
    if tier == "enterprise" and any(count is not None and count < 1 for count in (seats, nodes)):
        raise ValueError("Enterprise seat and node counts must be positive when provided")
    if tier == "enterprise" and not any(count is not None and count > 0 for count in (seats, nodes)):
        raise ValueError("Enterprise grants require a positive seat count or node count")

    now = datetime.datetime.now(datetime.timezone.utc)
    expiry = now + datetime.timedelta(days=days)
    
    payload = {
        "license_version": 1,
        "sub": customer.lower() if tier == "team" else organization_id,
        "tier": tier,
        "org_id": organization_id,
        "exp": int(expiry.timestamp()),
        "iss": "yamlr-entitlement",
        "aud": "yamlr",
        "iat": int(now.timestamp())
    }

    if tier == "team":
        payload.update({"email": customer.lower(), "seats": 1, "org_seats": seats})
    else:
        if seats is not None:
            payload["seats"] = seats
        if nodes is not None:
            payload["nodes"] = nodes
    
    # Standard: RS256 (RSA with SHA-256) matching native_verify_token in native_core
    private_key = _private_key_from_environment()
    token = jwt.encode(payload, private_key, algorithm="RS256")
    
    output_path = Path(f"license_{customer.replace(' ', '_').lower()}.jwt")
    output_path.write_text(token)
    
    print(f"✅ License generated for: {customer}")
    print(f"🏢 Organization: {organization_id}")
    print(f"🎟️  Contract: {seats or 0} seats, {nodes or 0} nodes")
    print(f"📅 Expiry: {expiry.strftime('%Y-%m-%d')}")
    print(f" Saved to: {output_path}")
    print("\n[INSTRUCTION] Send this signed grant to the customer. Activate it with:")
    print("  yamlr auth activate <SIGNED_LICENSE_TOKEN>")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Yamlr Founder License Generator")
    parser.add_argument("--mid", default="", help="Deprecated compatibility option; licenses are no longer machine-bound")
    parser.add_argument("--customer", required=True, help="Named developer email for Team; customer label for Enterprise")
    parser.add_argument("--tier", default="TEAM", choices=["TEAM", "ENTERPRISE", "PRO"], help="License tier; PRO is a legacy alias for TEAM")
    parser.add_argument("--organization-id", help="Stable organization identifier (defaults to customer name)")
    parser.add_argument("--seats", type=int, help="Contracted developer seats")
    parser.add_argument("--nodes", type=int, help="Contracted Enterprise nodes")
    parser.add_argument("--days", type=int, default=365, help="Validity in days")
    
    args = parser.parse_args()
    try:
        generate_license(args.mid, args.customer, args.tier, args.days, args.organization_id, args.seats, args.nodes)
    except ValueError as error:
        parser.error(str(error))
