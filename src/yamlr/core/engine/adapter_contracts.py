from __future__ import annotations

from enum import Enum, auto


class AdapterContract(Enum):
    """
    Contracts governing Yamlr Enterprise (Pro) custom remediation adapters.
    """

    ADD_ONLY = auto()  # Can only add new fields/keys
    NO_DELETIONS = auto()  # Can modify existing, but cannot remove fields
    SELECTORS_FROZEN = auto()  # Cannot modify spec.selector or metadata.labels (for selector-driven kinds)
    BREAK_GLASS = auto()  # Unlimited access, requires --allow-break-glass-adapters


class ContractViolationError(Exception):
    """
    Raised when an adapter violates its registered capability contract.
    """

    def __init__(self, rule_id: str, contract: str, path: str, message: str):
        self.rule_id = rule_id
        self.contract = contract
        self.path = path
        self.message = message
        super().__init__(f"AdapterViolation[rule_id={rule_id}, contract={contract}, path={path}]: {message}")
