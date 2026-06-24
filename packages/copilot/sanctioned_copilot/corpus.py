"""Build the citable retrieval corpus from policies and the runbook/domain docs.

Each policy becomes several focused, keyword-rich documents (overview, FOIR, LTV,
CIBIL, self-employed, property), and each Markdown ``##`` section of the runbook
and domain reference becomes one document. Every document carries a citation that
points an operator back to its source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sanctioned.registry import Registry
from sanctioned.schemas.policy import LenderPolicy


@dataclass(frozen=True)
class Document:
    """One retrievable, citable unit of the corpus."""

    id: str
    citation: str  # human-facing label, e.g. "psu_bank · CIBIL bands"
    source: str  # provenance path, e.g. "policies/psu_bank.yaml"
    section: str  # short section key, e.g. "cibil"
    text: str
    lender_id: str | None = None


def _policy_documents(policy: LenderPolicy) -> list[Document]:
    src = f"policies/{policy.lender_id}.yaml"
    name = policy.lender_name
    lid = policy.lender_id

    def doc(section: str, label: str, text: str) -> Document:
        return Document(
            id=f"{lid}:{section}",
            citation=f"{lid} · {label}",
            source=src,
            section=section,
            text=text,
            lender_id=lid,
        )

    foir = "; ".join(
        f"income up to {b.up_to_nmi or 'any'} -> {b.cap_pct}% cap" for b in policy.foir.salaried
    )
    ltv = "; ".join(
        f"loan up to {b.up_to_amount or 'any'} -> {b.max_ltv_pct}% LTV" for b in policy.ltv_bands
    )
    cibil = "; ".join(
        (
            f"thin file -> {t.decision.value}"
            if t.min_score == -1
            else f"{t.min_score}-{t.max_score} -> {t.decision.value}"
        )
        + (f" at {t.rate_pct}%" if t.rate_pct is not None else "")
        for t in policy.cibil_tiers
    )
    products = ", ".join(p.value.replace("_", " ").lower() for p in policy.products)

    return [
        doc(
            "overview",
            "overview",
            f"{name} is a {policy.lender_type.value.replace('_', ' ').lower()} lender. "
            f"It funds {products}. Maximum tenure {policy.tenure.max_years} years. "
            f"Net-monthly-income multiplier up to {policy.nmi_multiplier.max}x. "
            f"Loan size from {policy.limits.min_loan} to {policy.limits.max_loan} rupees.",
        ),
        doc("foir", "FOIR caps", f"{name} FOIR caps for salaried borrowers: {foir}."),
        doc("ltv", "LTV bands", f"{name} loan-to-value bands by amount: {ltv}."),
        doc(
            "cibil",
            "CIBIL bands",
            f"{name} CIBIL bands, decisions and indicative interest rates: {cibil}. "
            f"Thin or no credit file is encoded as CIBIL -1.",
        ),
        doc(
            "self_employed",
            "self-employed",
            f"{name} requires self-employed borrowers to have at least "
            f"{policy.self_employed.min_business_vintage_years} years of business vintage and "
            f"{policy.self_employed.itr_years_required} years of ITR history.",
        ),
        doc(
            "property",
            "property rules",
            f"{name} property acceptance and LTV overrides: "
            + (
                "; ".join(
                    f"{r.type.value.replace('_', ' ').lower()} "
                    + ("allowed" if r.allowed else "not funded")
                    + (f" at {r.ltv_override_pct}% LTV" if r.ltv_override_pct else "")
                    for r in policy.property_rules
                )
                or "standard acceptance for resale and builder properties"
            )
            + ".",
        ),
    ]


def _markdown_documents(path: Path, label: str) -> list[Document]:
    if not path.exists():
        return []
    documents: list[Document] = []
    heading = "intro"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            slug = heading.lower().replace(" ", "_")[:40]
            documents.append(
                Document(
                    id=f"{label}:{slug}",
                    citation=f"{label} · {heading}",
                    source=f"docs/{path.name}",
                    section=slug,
                    text=f"{heading}. {body}",
                )
            )

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            flush()
            heading = line[3:].strip()
            buffer = []
        elif not line.startswith("# "):
            buffer.append(line)
    flush()
    return documents


def build_corpus(registry: Registry, docs_dir: Path) -> list[Document]:
    """Assemble the full corpus from the registry and the docs directory."""
    documents: list[Document] = []
    for policy in registry:
        documents.extend(_policy_documents(policy))
    documents.extend(_markdown_documents(docs_dir / "runbook.md", "runbook"))
    documents.extend(_markdown_documents(docs_dir / "domain.md", "domain"))
    return documents
