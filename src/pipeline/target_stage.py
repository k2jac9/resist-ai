"""Stage 1: target discovery and druggability scoring.

Identifies druggable AMR targets for a pathogen via local pathogen DB
(or hardcoded fallback), then enriches each with ESMFold structure
prediction and ESM-2 druggability scoring when NIM is available.
"""
from __future__ import annotations

import logging
from typing import Any

from ..models.schemas import TargetResult
from .clients import get_nim
from .demo_data import DEMO_SEQUENCES

logger = logging.getLogger(__name__)


FALLBACK_TARGETS: dict[str, list[dict[str, str]]] = {
    "acinetobacter_baumannii": [
        {"name": "NDM-1", "pdb": "3SPU", "uniprot": "C7C422", "function": "Metallo-beta-lactamase (Class B)"},
        {"name": "OXA-23", "pdb": "4JF4", "uniprot": "Q2L4R8", "function": "Class D beta-lactamase"},
        {"name": "PBP3", "pdb": "6V1M", "uniprot": "A0A0D5YPF0", "function": "Peptidoglycan synthesis"},
        {"name": "LpxC", "pdb": "3UHM", "uniprot": "", "function": "Lipid A biosynthesis"},
    ],
    "staphylococcus_aureus": [
        {"name": "PBP2a", "pdb": "1VQQ", "uniprot": "P07944", "function": "Altered PBP, beta-lactam resistance"},
        {"name": "DNA Gyrase", "pdb": "2XCS", "uniprot": "P0A0K8", "function": "DNA replication"},
    ],
    "klebsiella_pneumoniae": [
        {"name": "KPC-2", "pdb": "5UL8", "uniprot": "Q6PT52", "function": "Class A carbapenemase"},
        {"name": "NDM-1", "pdb": "3SPU", "uniprot": "C7C422", "function": "Metallo-beta-lactamase"},
    ],
    "pseudomonas_aeruginosa": [
        {"name": "MexB", "pdb": "3W9I", "uniprot": "P52477", "function": "RND efflux pump"},
        {"name": "LasR", "pdb": "2UV0", "uniprot": "P25084", "function": "Quorum sensing regulator"},
    ],
}


def compute_druggability(sequence: str) -> float:
    """Heuristic druggability score from sequence length and hydrophobic fraction."""
    seq_len = len(sequence)
    if 200 <= seq_len <= 800:
        length_score = 0.90
    elif 100 <= seq_len < 200:
        length_score = 0.75
    else:
        length_score = 0.60
    hydrophobic = set("AILMFWVP")
    hydro_frac = sum(1 for aa in sequence if aa in hydrophobic) / max(seq_len, 1)
    hydro_score = min(1.0, hydro_frac / 0.35)
    return round(0.5 * length_score + 0.5 * hydro_score, 3)


def get_pathogen_targets(pathogen_name: str) -> list[dict[str, Any]]:
    """Load target data from PathogenManager, falling back to FALLBACK_TARGETS."""
    try:
        from ..data.pathogens import PathogenManager
        mgr = PathogenManager()
        info = mgr.get_pathogen(pathogen_name)
        if info and "key_targets" in info:
            return info["key_targets"]
    except Exception as exc:
        logger.debug("PathogenManager unavailable (%s); using fallback targets", exc)
    return FALLBACK_TARGETS.get(pathogen_name, FALLBACK_TARGETS["acinetobacter_baumannii"])


class TargetAnalyzer:
    """Stage 1: Identify druggable targets using ESMFold + ESM-2."""

    def discover_targets(
        self, pathogen_name: str, use_nim: bool = True
    ) -> list[TargetResult]:
        """Return druggable targets, optionally folded via ESMFold."""
        from .stages import stage_fold_protein, stage_druggability

        target_db = get_pathogen_targets(pathogen_name)
        nim = get_nim() if use_nim else None
        results: list[TargetResult] = []

        for t in target_db:
            name = t["name"]
            sequence = DEMO_SEQUENCES.get(name, "")

            structure_data = ""
            fold = stage_fold_protein(nim, sequence)
            if fold["success"]:
                structure_data = f"ESMFold ({fold['elapsed_ms']:.0f}ms)"
                logger.info(
                    "ESMFold folded %s: %d residues in %.0fms",
                    name, fold["sequence_length"], fold["elapsed_ms"],
                )

            drug_result = stage_druggability(sequence) if sequence else {"success": False}
            if drug_result["success"]:
                score = drug_result["score"]
                model_used = drug_result.get("model", "")
                if "ESM-2" in model_used:
                    logger.info("ESM-2 druggability %s: %.3f (%s)", name, score, model_used)
            else:
                # Deterministic structure/sequence-based score; no random fabrication.
                score = compute_druggability(sequence) if sequence else 0.5

            function_desc = t.get("function", "")
            if structure_data:
                function_desc += f" [{structure_data}]"

            results.append(TargetResult(
                name=name,
                pdb_code=t.get("pdb", "N/A"),
                uniprot_id=t.get("uniprot", ""),
                function=function_desc,
                druggability_score=score,
                pathogen=pathogen_name,
                resistance_mechanism=t.get("function", ""),
            ))

        results.sort(key=lambda r: r.druggability_score, reverse=True)
        return results
