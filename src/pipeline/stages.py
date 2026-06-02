"""Shared pipeline stage functions used by both orchestrator and SDK.

Each function takes a NIM client (or None) and domain inputs, returning
plain dicts so that callers can map results into their own schema types.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)



def stage_genomics(nim: Any, sequence: str, num_tokens: int = 128) -> dict:
    """Run Evo2 genomic analysis. Returns {success, generated_length, elapsed_ms, model}."""
    if not nim or not nim.available or not sequence:
        return {"success": False}
    try:
        result = nim.generate_dna(sequence, num_tokens=num_tokens)
        if result.success:
            return {
                "success": True,
                "generated_length": result.output_length,
                "elapsed_ms": result.elapsed_ms,
                "model": "Evo2-40b (NVIDIA NIM)",
            }
    except Exception as exc:
        logger.warning("Evo2 analysis failed: %s", exc)
    return {"success": False}


def heuristic_binding_score(smiles: str, target_name: str = "") -> dict:
    """Deterministic, structure-based binding estimate (no NIM required).

    Derived from RDKit molecular descriptors (drug-like MW/LogP windows),
    so the same molecule always yields the same score. Returned values are
    explicitly tagged ``model="heuristic_docking"`` so callers never present
    them as Boltz-2 predictions.

    Returns {affinity, confidence, model}.
    """
    from src.utils.chemistry import compute_descriptors

    desc = compute_descriptors(smiles) if smiles else None
    if desc is None:
        # No structure: deterministic-but-clearly-low placeholder.
        return {"affinity": 0.4, "confidence": 0.3, "model": "heuristic_docking"}

    mw = desc.get("MW", 400.0)
    log_p = desc.get("LogP", 2.5)
    mw_score = max(0.0, 1.0 - abs(mw - 400.0) / 400.0)
    logp_score = max(0.0, 1.0 - abs(log_p - 2.5) / 5.0)
    affinity = round(min(0.97, 0.35 + 0.45 * mw_score + 0.2 * logp_score), 3)
    confidence = round(min(0.9, 0.5 + 0.4 * mw_score), 3)
    return {"affinity": affinity, "confidence": confidence, "model": "heuristic_docking"}


# Lazy-loaded ESM-2 client (heavy — 650M params)
_esm2 = None


def _get_esm2():
    global _esm2
    if _esm2 is None:
        try:
            from src.pipeline.target_discovery.esm2_client import ESM2Client
            _esm2 = ESM2Client()
        except Exception as exc:
            logger.warning("ESM-2 init failed: %s", exc)
    return _esm2


def stage_druggability(sequence: str) -> dict:
    """Score druggability using ESM-2 protein embeddings (local HuggingFace).

    Returns {success, score, model, embedding_dim, elapsed_ms}.
    Falls back to heuristic if ESM-2 unavailable.
    """
    if not sequence:
        return {"success": False}

    import time
    t0 = time.time()

    esm2 = _get_esm2()
    if esm2 and esm2._available:
        try:
            score = esm2.predict_druggability(sequence)
            elapsed = (time.time() - t0) * 1000
            return {
                "success": True,
                "score": score,
                "model": "ESM-2 650M (HuggingFace, local)",
                "embedding_dim": 1280,
                "elapsed_ms": elapsed,
            }
        except Exception as exc:
            logger.warning("ESM-2 druggability failed: %s", exc)

    # Heuristic fallback
    seq_len = len(sequence)
    hydrophobic = set("AILMFWVP")
    hydro_frac = sum(1 for aa in sequence if aa in hydrophobic) / max(seq_len, 1)
    length_score = 0.90 if 200 <= seq_len <= 800 else (0.75 if 100 <= seq_len < 200 else 0.60)
    score = round(0.5 * length_score + 0.5 * min(1.0, hydro_frac / 0.35), 3)
    elapsed = (time.time() - t0) * 1000
    return {
        "success": True,
        "score": score,
        "model": "heuristic (sequence properties)",
        "elapsed_ms": elapsed,
    }


def stage_fold_protein(nim: Any, sequence: str) -> dict:
    """Fold a protein via ESMFold. Returns {success, pdb_string, elapsed_ms, sequence_length}."""
    if not nim or not nim.available or not sequence:
        return {"success": False}
    try:
        result = nim.fold_protein(sequence)
        if result.success:
            return {
                "success": True,
                "pdb_string": result.pdb_string,
                "elapsed_ms": result.elapsed_ms,
                "sequence_length": result.sequence_length,
            }
    except Exception as exc:
        logger.warning("ESMFold failed: %s", exc)
    return {"success": False}



def stage_screen_drug(
    nim: Any, target_sequence: str, smiles: str
) -> dict:
    """Screen a single drug against a target via Boltz-2."""
    if not nim or not nim.available or not target_sequence or not smiles:
        return {"success": False}
    try:
        result = nim.predict_binding(target_sequence, smiles)
        if result.success:
            return {
                "success": True,
                "confidence": result.confidence_score,
                "complex_plddt": result.complex_plddt,
                "ptm_score": result.ptm_score,
                "iptm_score": result.iptm_score,
                "ligand_iptm": result.ligand_iptm_score,
                "structure_cif": result.structure_cif,
                "raw": result.raw_affinities,
            }
    except Exception as exc:
        logger.warning("Boltz-2 screening failed: %s", exc)
    return {"success": False}



def stage_dock(
    nim: Any,
    protein_pdb: str,
    smiles: str,
    num_poses: int = 3,
) -> dict:
    """Run DiffDock molecular docking. Returns {success, num_poses, ligand_positions, ...}."""
    if not nim or not nim.available or not protein_pdb or not smiles:
        return {"success": False}
    try:
        result = nim.dock_molecule(protein_pdb, smiles, num_poses=num_poses)
        if result.success:
            return {
                "success": True,
                "num_poses": result.num_poses,
                "ligand_positions": result.ligand_positions,
                "position_confidence": result.position_confidence,
            }
    except Exception as exc:
        logger.warning("DiffDock failed: %s", exc)
    return {"success": False}



def stage_generate_molecules(
    nim: Any,
    seed_smiles: str,
    num_molecules: int = 3,
    property_name: str = "QED",
    min_similarity: float = 0.3,
) -> dict:
    """Generate novel molecules via MolMIM. Returns {success, molecules, num_generated, score_type}."""
    if not nim or not nim.available or not seed_smiles:
        return {"success": False, "molecules": []}
    try:
        result = nim.generate_molecules(
            seed_smiles=seed_smiles,
            num_molecules=num_molecules,
            property_name=property_name,
            min_similarity=min_similarity,
        )
        if result.success:
            molecules = []
            for mol in result.molecules:
                molecules.append({
                    "smiles": mol.get("sample", mol.get("smiles", mol.get("smi", ""))),
                    "score": mol.get("score", mol.get(property_name, 0.0)),
                })
            return {
                "success": True,
                "molecules": molecules,
                "num_generated": result.num_generated,
                "score_type": result.score_type or property_name,
            }
    except Exception as exc:
        logger.warning("MolMIM generation failed: %s", exc)
    return {"success": False, "molecules": []}



def stage_design_binder(
    nim: Any,
    protein_pdb: str,
    contigs: str = "10-40/A1-60/10-40",
) -> dict:
    """Design protein binder via RFdiffusion + ProteinMPNN."""
    if not nim or not nim.available or not protein_pdb:
        return {"success": False}
    try:
        rf_result = nim.design_binder(protein_pdb, contigs=contigs)
        if not rf_result.success:
            return {"success": False}

        mpnn_result = nim.design_sequence(rf_result.pdb_string)
        if mpnn_result.success:
            return {
                "success": True,
                "backbone_pdb": rf_result.pdb_string,
                "num_residues": rf_result.num_residues,
                "rfdiffusion_ms": rf_result.elapsed_ms,
                "sequences": mpnn_result.sequences,
                "num_sequences": mpnn_result.num_sequences,
            }
        # Backbone succeeded but sequence design failed
        return {
            "success": False,
            "backbone_pdb": rf_result.pdb_string,
            "num_residues": rf_result.num_residues,
            "rfdiffusion_ms": rf_result.elapsed_ms,
        }
    except Exception as exc:
        logger.warning("Binder design failed: %s", exc)
    return {"success": False}



def stage_safety_score(drug_name: str, smiles: str = "") -> dict:
    """Run ADMET + off-target safety scoring.

    Uses the deterministic, RDKit-descriptor-based ADMET predictor and the
    Tanimoto-similarity off-target analyzer. Scores are derived from the
    molecule's actual structure (``smiles``), not random numbers. When no
    SMILES is available the result is flagged as unavailable rather than
    fabricated.

    Returns a dict with a ``provenance`` field describing how scores were
    produced so callers never present heuristics as measured values.
    """
    if not smiles or not smiles.strip():
        # No structure to analyze -- do not invent numbers.
        return {
            "toxicity": 0.0,
            "safety_score": 0.0,
            "admet": {
                "absorption": 0.0, "distribution": 0.0, "metabolism": 0.0,
                "excretion": 0.0, "toxicity_score": 0.0,
                "oral_bioavailability": False, "bbb_penetration": False,
                "herg_liability": False,
            },
            "off_targets": [],
            "high_risk": False,
            "flags": ["safety_unavailable_no_structure"],
            "recommendation": "insufficient_data",
            "provenance": "unavailable (no SMILES provided)",
        }

    from src.pipeline.safety_prediction.admet_predictor import ADMETPredictor
    from src.pipeline.safety_prediction.off_target_analyzer import OffTargetAnalyzer

    try:
        admet_full = ADMETPredictor().predict_admet(smiles)
    except Exception as exc:
        logger.warning("ADMET prediction failed for %s: %s", drug_name, exc)
        return {
            "toxicity": 0.0, "safety_score": 0.0,
            "admet": {
                "absorption": 0.0, "distribution": 0.0, "metabolism": 0.0,
                "excretion": 0.0, "toxicity_score": 0.0,
                "oral_bioavailability": False, "bbb_penetration": False,
                "herg_liability": False,
            },
            "off_targets": [], "high_risk": False,
            "flags": ["safety_unavailable_invalid_structure"],
            "recommendation": "insufficient_data",
            "provenance": f"unavailable (ADMET error: {exc})",
        }

    tox_d = admet_full.toxicity
    cyp = admet_full.metabolism
    # Collapse the rich ADMET dicts into the schema's per-category quality
    # scores (higher = more favorable), all derived from real descriptors.
    hia = admet_full.absorption.get("human_intestinal_absorption", 0.0)
    ppb = admet_full.distribution.get("plasma_protein_binding", 50.0)
    cyp_mean = (sum(cyp.values()) / len(cyp)) if cyp else 0.0
    clearance = admet_full.excretion.get("total_clearance", 0.5)
    herg = tox_d.get("herg_inhibition", 0.0)
    toxicity_score = round(
        (herg + tox_d.get("ames_mutagenicity", 0.0)
         + tox_d.get("hepatotoxicity", 0.0)) / 3.0, 3
    )

    admet = {
        "absorption": round(hia / 100.0, 3),
        "distribution": round(1.0 - min(1.0, ppb / 100.0), 3),
        "metabolism": round(1.0 - min(1.0, cyp_mean), 3),
        "excretion": round(min(1.0, clearance / 2.0), 3),
        "toxicity_score": toxicity_score,
        "oral_bioavailability": bool(hia >= 30.0),
        "bbb_penetration": bool(admet_full.distribution.get("bbb_penetration", 0.0) > 0.5),
        "herg_liability": bool(herg > 0.5),
    }

    ot_report = OffTargetAnalyzer().analyze_off_targets(smiles)
    off_targets: list[dict] = []
    for ot in ot_report.off_targets:
        sim = ot.similarity_score
        risk = "high" if sim > 0.6 else ("medium" if sim > 0.35 else "low")
        off_targets.append({
            "protein_name": ot.protein_name,
            "similarity": sim,
            "risk_level": risk,
            "tissue": ot.tissue_expression,
        })
    high_risk = ot_report.risk_level == "high"

    flags: list[str] = []
    if admet["herg_liability"]:
        flags.append("hERG_liability")
    if high_risk:
        flags.append("off_target_high_risk")
    if toxicity_score > 0.3:
        flags.append("elevated_toxicity")

    return {
        "toxicity": toxicity_score,
        "safety_score": admet_full.overall_safety_score,
        "admet": admet,
        "off_targets": off_targets,
        "high_risk": high_risk,
        "flags": flags,
        "recommendation": "caution" if flags else "proceed",
        "provenance": "RDKit ADMET heuristic + Tanimoto off-target panel",
    }
