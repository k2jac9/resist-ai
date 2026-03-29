"""Shared data schemas for the AMR-AI pipeline.

Defines all dataclasses used across target discovery, drug screening,
safety prediction, and pipeline orchestration modules.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Target Discovery
# ---------------------------------------------------------------------------

@dataclass
class TargetResult:
    """A druggable protein target identified during target discovery."""

    name: str
    pdb_code: str
    uniprot_id: str = ""
    function: str = ""
    druggability_score: float = 0.0
    pathogen: str = ""
    resistance_mechanism: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetResult:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        return (
            f"Target({self.name}, PDB={self.pdb_code}, "
            f"druggability={self.druggability_score:.2f})"
        )


# ---------------------------------------------------------------------------
# Drug Screening
# ---------------------------------------------------------------------------

@dataclass
class BindingResult:
    """Result of a single docking/binding affinity prediction."""

    drug_name: str
    smiles: str
    target_name: str
    binding_affinity: float = 0.0
    affinity_probability: float = 0.0
    docking_score: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BindingResult:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        return (
            f"Binding({self.drug_name} -> {self.target_name}, "
            f"affinity={self.binding_affinity:.3f})"
        )


@dataclass
class ScreeningHit:
    """A drug that passed binding threshold during virtual screening."""

    rank: int
    drug_name: str
    smiles: str
    target_name: str
    binding_affinity: float = 0.0
    confidence: float = 0.0
    mechanism_of_action: str = ""
    clinical_phase: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreeningHit:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        return (
            f"Hit #{self.rank}: {self.drug_name} "
            f"(affinity={self.binding_affinity:.3f}, conf={self.confidence:.2f})"
        )


@dataclass
class ScreeningResults:
    """Aggregated results from a virtual drug screening run."""

    target_name: str
    compounds_screened: int = 0
    hits: list[ScreeningHit] = field(default_factory=list)
    threshold_used: float = 0.5
    model_used: str = "demo"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["hits"] = [h.to_dict() if isinstance(h, ScreeningHit) else h for h in self.hits]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreeningResults:
        hits_raw = data.pop("hits", [])
        hits = [ScreeningHit.from_dict(h) if isinstance(h, dict) else h for h in hits_raw]
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered, hits=hits)

    def __str__(self) -> str:
        return (
            f"Screening({self.target_name}: {len(self.hits)} hits "
            f"from {self.compounds_screened} compounds)"
        )


# ---------------------------------------------------------------------------
# Safety Prediction
# ---------------------------------------------------------------------------

@dataclass
class ADMETResult:
    """ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) profile."""

    drug_name: str
    absorption: float = 0.0
    distribution: float = 0.0
    metabolism: float = 0.0
    excretion: float = 0.0
    toxicity_score: float = 0.0
    oral_bioavailability: bool = True
    bbb_penetration: bool = False
    herg_liability: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ADMETResult:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        return f"ADMET({self.drug_name}, tox={self.toxicity_score:.2f})"


@dataclass
class OffTarget:
    """A single predicted off-target interaction."""

    protein_name: str
    similarity: float = 0.0
    risk_level: str = "low"
    tissue: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OffTarget:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        return f"OffTarget({self.protein_name}, risk={self.risk_level})"


@dataclass
class OffTargetReport:
    """Aggregated off-target interaction report for a compound."""

    drug_name: str
    off_targets: list[OffTarget] = field(default_factory=list)
    overall_risk: str = "low"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["off_targets"] = [
            ot.to_dict() if isinstance(ot, OffTarget) else ot for ot in self.off_targets
        ]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OffTargetReport:
        ots_raw = data.pop("off_targets", [])
        ots = [OffTarget.from_dict(o) if isinstance(o, dict) else o for o in ots_raw]
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered, off_targets=ots)

    def __str__(self) -> str:
        return (
            f"OffTargetReport({self.drug_name}, "
            f"{len(self.off_targets)} off-targets, risk={self.overall_risk})"
        )


@dataclass
class SafetyReport:
    """Combined safety assessment for a drug candidate."""

    drug_name: str
    smiles: str = ""
    safety_score: float = 0.0
    admet: Optional[ADMETResult] = None
    off_target_report: Optional[OffTargetReport] = None
    flags: list[str] = field(default_factory=list)
    recommendation: str = "proceed"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.admet:
            d["admet"] = self.admet.to_dict()
        if self.off_target_report:
            d["off_target_report"] = self.off_target_report.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SafetyReport:
        admet_raw = data.pop("admet", None)
        ot_raw = data.pop("off_target_report", None)
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        obj = cls(**filtered)
        if isinstance(admet_raw, dict):
            obj.admet = ADMETResult.from_dict(admet_raw)
        if isinstance(ot_raw, dict):
            obj.off_target_report = OffTargetReport.from_dict(ot_raw)
        return obj

    def __str__(self) -> str:
        return (
            f"SafetyReport({self.drug_name}, score={self.safety_score:.2f}, "
            f"rec={self.recommendation})"
        )


# ---------------------------------------------------------------------------
# Pipeline Output
# ---------------------------------------------------------------------------

@dataclass
class DrugCandidate:
    """A ranked drug candidate from the full pipeline."""

    rank: int
    drug_name: str
    smiles: str
    target_name: str
    binding_affinity: float = 0.0
    safety_score: float = 0.0
    overall_score: float = 0.0
    regulatory_pathway: str = "505(b)(2)"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DrugCandidate:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def __str__(self) -> str:
        return (
            f"#{self.rank} {self.drug_name} "
            f"(score={self.overall_score:.3f}, safety={self.safety_score:.2f})"
        )


@dataclass
class PipelineResults:
    """Complete results from a full AMR-AI pipeline run."""

    pathogen: str
    targets: list[TargetResult] = field(default_factory=list)
    screening_results: list[ScreeningResults] = field(default_factory=list)
    safety_reports: list[SafetyReport] = field(default_factory=list)
    top_candidates: list[DrugCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pathogen": self.pathogen,
            "targets": [t.to_dict() for t in self.targets],
            "screening_results": [s.to_dict() for s in self.screening_results],
            "safety_reports": [r.to_dict() for r in self.safety_reports],
            "top_candidates": [c.to_dict() for c in self.top_candidates],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineResults:
        return cls(
            pathogen=data["pathogen"],
            targets=[TargetResult.from_dict(t) for t in data.get("targets", [])],
            screening_results=[
                ScreeningResults.from_dict(s) for s in data.get("screening_results", [])
            ],
            safety_reports=[
                SafetyReport.from_dict(r) for r in data.get("safety_reports", [])
            ],
            top_candidates=[
                DrugCandidate.from_dict(c) for c in data.get("top_candidates", [])
            ],
            metadata=data.get("metadata", {}),
        )

    def __str__(self) -> str:
        return (
            f"PipelineResults({self.pathogen}: "
            f"{len(self.targets)} targets, "
            f"{len(self.top_candidates)} candidates)"
        )
