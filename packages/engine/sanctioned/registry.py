"""Load and index lender policies from YAML.

Two design points matter here:

* **Decimal-safe parsing.** YAML scalars like ``8.10`` would otherwise become
  binary floats and corrupt money/rate arithmetic. We parse every float scalar
  straight into :class:`~decimal.Decimal` so values are exact end to end.
* **Validation on load.** A policy is only admitted to the registry after passing
  :func:`~sanctioned.validation.policy_validator.validate_policy`, so a malformed
  rate card fails loudly at startup rather than mid-match.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from sanctioned.schemas.policy import LenderPolicy
from sanctioned.validation.policy_validator import validate_policy

_POLICY_GLOBS = ("*.yaml", "*.yml")


class _DecimalSafeLoader(yaml.SafeLoader):
    """A SafeLoader that yields :class:`Decimal` for YAML float scalars."""


def _construct_decimal(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> Decimal:
    return Decimal(loader.construct_scalar(node))


_DecimalSafeLoader.add_constructor("tag:yaml.org,2002:float", _construct_decimal)


def load_policy_data(path: Path) -> dict[str, Any]:
    """Read a policy YAML file into a raw dict, parsing floats as ``Decimal``."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=_DecimalSafeLoader)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level")
    return data


def load_policy(path: Path, *, validate: bool = True) -> LenderPolicy:
    """Parse a single policy file into a :class:`LenderPolicy`.

    When ``validate`` is true (the default) the policy must also satisfy every
    business invariant in :func:`validate_policy`.
    """
    policy = LenderPolicy.model_validate(load_policy_data(path))
    if validate:
        validate_policy(policy)
    return policy


class Registry:
    """An immutable, in-memory collection of lender policies keyed by ``lender_id``."""

    def __init__(self, policies: dict[str, LenderPolicy]) -> None:
        self._policies = dict(policies)

    def get(self, lender_id: str) -> LenderPolicy:
        """Return the policy for ``lender_id`` or raise ``KeyError`` if absent."""
        return self._policies[lender_id]

    def __iter__(self) -> Iterator[LenderPolicy]:
        return iter(self._policies.values())

    def __len__(self) -> int:
        return len(self._policies)

    def __contains__(self, lender_id: object) -> bool:
        return lender_id in self._policies


def load_registry(directory: Path, *, validate: bool = True) -> Registry:
    """Load every policy file under ``directory`` into a :class:`Registry`.

    Files are processed in sorted order for deterministic behaviour. A duplicate
    ``lender_id`` is a hard error, as is any file that fails parsing or validation.
    """
    policies: dict[str, LenderPolicy] = {}
    paths = sorted(p for glob in _POLICY_GLOBS for p in directory.glob(glob))
    for path in paths:
        policy = load_policy(path, validate=validate)
        if policy.lender_id in policies:
            raise ValueError(f"duplicate lender_id '{policy.lender_id}' (from {path.name})")
        policies[policy.lender_id] = policy
    return Registry(policies)
