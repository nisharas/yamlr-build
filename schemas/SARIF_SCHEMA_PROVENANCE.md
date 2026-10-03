# SARIF validation schema

`sarif-schema-2.1.0.json` is the unmodified OASIS SARIF 2.1.0 errata01
schema, downloaded on 2026-10-01 from:

https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json

SHA-256: `c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e`.

The schema is used offline by development/release CI; validation never downloads
references at runtime. The validator rejects unexpected changes to this file.
Schema updates require review of upstream source, checksum, and validation results.

This upstream material remains subject to the OASIS document terms:
https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os-complete.html
It must be included in the third-party material inventory and redistribution
review under remediation item 0.4. No legal clearance is implied here.
