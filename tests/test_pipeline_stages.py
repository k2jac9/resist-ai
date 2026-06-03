"""Tests for src/pipeline/stages.py -- the shared NIM-gated stage functions.

Offline-safe: a fake NIM client supplies deterministic results, and the
ESM-2 loader is patched out so the heuristic druggability path runs without
downloading the 650M model.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.pipeline import stages
from src.pipeline.stages import (
    _generate_off_targets,
    stage_design_binder,
    stage_dock,
    stage_druggability,
    stage_fold_protein,
    stage_generate_molecules,
    stage_genomics,
    stage_safety_score,
    stage_screen_drug,
)


# -- Fake NIM client -----------------------------------------------------------

class FakeNIM:
    """Minimal stand-in for NIMClient returning canned, successful results."""

    def __init__(self, available=True):
        self.available = available

    def generate_dna(self, sequence, num_tokens=128):
        return SimpleNamespace(success=True, output_length=num_tokens, elapsed_ms=12.0)

    def fold_protein(self, sequence):
        return SimpleNamespace(
            success=True, pdb_string="ATOM...", elapsed_ms=34.0,
            sequence_length=len(sequence),
        )

    def predict_binding(self, target_sequence, smiles):
        return SimpleNamespace(
            success=True, confidence_score=0.8, complex_plddt=0.7,
            ptm_score=0.6, iptm_score=0.5, ligand_iptm_score=0.4,
            structure_cif="data_cif", raw_affinities={"kd": 1.2},
        )

    def dock_molecule(self, protein_pdb, smiles, num_poses=3):
        return SimpleNamespace(
            success=True, num_poses=num_poses,
            ligand_positions=[[0, 0, 0]] * num_poses,
            position_confidence=[0.9, 0.8, 0.7],
        )

    def generate_molecules(self, seed_smiles, num_molecules=3,
                           property_name="QED", min_similarity=0.3):
        mols = [{"sample": f"C{i}", "score": 0.5 + i * 0.1} for i in range(num_molecules)]
        return SimpleNamespace(
            success=True, molecules=mols, num_generated=num_molecules,
            score_type=property_name,
        )

    def design_binder(self, protein_pdb, contigs="10-40/A1-60/10-40"):
        return SimpleNamespace(
            success=True, pdb_string="BACKBONE", num_residues=60, elapsed_ms=99.0,
        )

    def design_sequence(self, pdb_string):
        return SimpleNamespace(success=True, sequences=["MKT", "MKV"], num_sequences=2)


# Each NIM-gated stage and the kwargs it needs to be invoked.
NIM_STAGES = [
    (stage_genomics, ("ATGC",), {}),
    (stage_fold_protein, ("MKLV",), {}),
    (stage_screen_drug, ("MKLV", "CCO"), {}),
    (stage_dock, ("ATOM...", "CCO"), {}),
    (stage_generate_molecules, ("CCO",), {}),
    (stage_design_binder, ("ATOM...",), {}),
]


# -- Guard clauses (no NIM / unavailable / empty inputs) -----------------------

class TestStageGuards:
    @pytest.mark.parametrize("fn,args,kwargs", NIM_STAGES)
    def test_none_nim_returns_failure(self, fn, args, kwargs):
        assert fn(None, *args, **kwargs)["success"] is False

    @pytest.mark.parametrize("fn,args,kwargs", NIM_STAGES)
    def test_unavailable_nim_returns_failure(self, fn, args, kwargs):
        assert fn(FakeNIM(available=False), *args, **kwargs)["success"] is False

    def test_genomics_empty_sequence(self):
        assert stage_genomics(FakeNIM(), "")["success"] is False

    def test_screen_drug_empty_smiles(self):
        assert stage_screen_drug(FakeNIM(), "MKLV", "")["success"] is False

    def test_generate_molecules_empty_seed_has_empty_list(self):
        result = stage_generate_molecules(FakeNIM(), "")
        assert result["success"] is False
        assert result["molecules"] == []


# -- Happy paths with the fake NIM ---------------------------------------------

class TestStageGenomics:
    def test_success(self):
        r = stage_genomics(FakeNIM(), "ATGC", num_tokens=64)
        assert r["success"] is True
        assert r["generated_length"] == 64
        assert "Evo2" in r["model"]

    def test_exception_is_swallowed(self):
        nim = FakeNIM()
        nim.generate_dna = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        assert stage_genomics(nim, "ATGC")["success"] is False


class TestStageFoldProtein:
    def test_success_reports_length(self):
        r = stage_fold_protein(FakeNIM(), "MKLVAA")
        assert r["success"] is True
        assert r["sequence_length"] == 6
        assert r["pdb_string"] == "ATOM..."


class TestStageScreenDrug:
    def test_success_maps_scores(self):
        r = stage_screen_drug(FakeNIM(), "MKLV", "CCO")
        assert r["success"] is True
        assert r["confidence"] == 0.8
        assert r["complex_plddt"] == 0.7
        assert r["raw"] == {"kd": 1.2}


class TestStageDock:
    def test_success(self):
        r = stage_dock(FakeNIM(), "ATOM...", "CCO", num_poses=2)
        assert r["success"] is True
        assert r["num_poses"] == 2


class TestStageGenerateMolecules:
    def test_success_normalizes_molecules(self):
        r = stage_generate_molecules(FakeNIM(), "CCO", num_molecules=2)
        assert r["success"] is True
        assert len(r["molecules"]) == 2
        assert r["molecules"][0]["smiles"] == "C0"
        assert r["score_type"] == "QED"

    def test_molecule_key_fallbacks(self):
        nim = FakeNIM()
        nim.generate_molecules = lambda **k: SimpleNamespace(
            success=True, num_generated=1, score_type="",
            molecules=[{"smi": "CCC", "QED": 0.9}],
        )
        r = stage_generate_molecules(nim, "CCO", property_name="QED")
        assert r["molecules"][0]["smiles"] == "CCC"
        assert r["molecules"][0]["score"] == 0.9
        # score_type falls back to property_name when empty
        assert r["score_type"] == "QED"


class TestStageDesignBinder:
    def test_full_success(self):
        r = stage_design_binder(FakeNIM(), "ATOM...")
        assert r["success"] is True
        assert r["num_residues"] == 60
        assert r["num_sequences"] == 2

    def test_backbone_ok_but_sequence_fails(self):
        nim = FakeNIM()
        nim.design_sequence = lambda pdb: SimpleNamespace(success=False)
        r = stage_design_binder(nim, "ATOM...")
        assert r["success"] is False
        assert r["num_residues"] == 60  # backbone info still surfaced

    def test_backbone_failure(self):
        nim = FakeNIM()
        nim.design_binder = lambda pdb, contigs=None: SimpleNamespace(success=False)
        assert stage_design_binder(nim, "ATOM...")["success"] is False


# -- Druggability (heuristic fallback, ESM-2 patched out) ----------------------

class TestStageDruggability:
    def test_empty_sequence(self):
        assert stage_druggability("")["success"] is False

    def test_heuristic_when_esm2_unavailable(self):
        with patch.object(stages, "_get_esm2", return_value=None):
            r = stage_druggability("MKLVAAILMFWVP" * 20)
        assert r["success"] is True
        assert "heuristic" in r["model"]
        assert 0.0 <= r["score"] <= 1.0
        assert "elapsed_ms" in r

    def test_heuristic_is_deterministic(self):
        seq = "MELPNIMHPVAKLSTALAAALMLSGC"
        with patch.object(stages, "_get_esm2", return_value=None):
            a = stage_druggability(seq)["score"]
            b = stage_druggability(seq)["score"]
        assert a == b

    def test_esm2_path_used_when_available(self):
        fake_esm = SimpleNamespace(_available=True, predict_druggability=lambda s: 0.77)
        with patch.object(stages, "_get_esm2", return_value=fake_esm):
            r = stage_druggability("MKLV")
        assert r["success"] is True
        assert r["score"] == 0.77
        assert "ESM-2" in r["model"]

    def test_esm2_exception_falls_back_to_heuristic(self):
        def boom(_s):
            raise RuntimeError("model error")
        fake_esm = SimpleNamespace(_available=True, predict_druggability=boom)
        with patch.object(stages, "_get_esm2", return_value=fake_esm):
            r = stage_druggability("MKLVAAILM")
        assert r["success"] is True
        assert "heuristic" in r["model"]


# -- Safety scoring (seeded, deterministic) ------------------------------------

class TestStageSafetyScore:
    def test_seeded_output_is_exact(self):
        r = stage_safety_score("drugX", seed=42)
        assert r["toxicity"] == 0.274
        assert r["safety_score"] == 0.726
        assert r["admet"]["herg_liability"] is False
        assert r["high_risk"] is False
        assert r["flags"] == []
        assert r["recommendation"] == "proceed"

    def test_safety_is_one_minus_toxicity(self):
        for seed in range(10):
            r = stage_safety_score("d", seed=seed)
            assert r["safety_score"] == round(1.0 - r["toxicity"], 3)

    def test_flags_trigger_caution(self):
        # seed=0 yields toxicity 0.346 (>0.3) and a high-risk off-target.
        r = stage_safety_score("d", seed=0)
        assert "elevated_toxicity" in r["flags"]
        assert "off_target_high_risk" in r["flags"]
        assert r["recommendation"] == "caution"

    def test_default_seed_is_stable_within_process(self):
        assert stage_safety_score("aspirin") == stage_safety_score("aspirin")

    def test_admet_keys_present(self):
        admet = stage_safety_score("d", seed=1)["admet"]
        for key in ("absorption", "distribution", "metabolism", "excretion",
                    "toxicity_score", "oral_bioavailability", "bbb_penetration",
                    "herg_liability"):
            assert key in admet


class TestGenerateOffTargets:
    def test_seeded_exact(self):
        ots = _generate_off_targets("drugX", 7)
        assert ots == [
            {"protein_name": "CYP2D6", "similarity": 0.61, "risk_level": "medium", "tissue": "liver"},
            {"protein_name": "GABAA", "similarity": 0.29, "risk_level": "low", "tissue": "CNS"},
        ]

    def test_count_between_one_and_three(self):
        for seed in range(30):
            ots = _generate_off_targets("d", seed)
            assert 1 <= len(ots) <= 3

    def test_risk_level_matches_similarity(self):
        for ot in _generate_off_targets("d", 5):
            sim = ot["similarity"]
            expected = "high" if sim > 0.7 else ("medium" if sim > 0.5 else "low")
            assert ot["risk_level"] == expected
