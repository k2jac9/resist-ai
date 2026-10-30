"""Scientific presentation tests: do not promote calculations to biological evidence."""
import json
import pytest


def test_descriptor_values_are_computed_for_ethanol():
    from src.research_integrity import descriptor_evidence
    e = descriptor_evidence("CCO")
    assert e["method"] == "RDKit molecular descriptors"
    assert e["values"]["molecular_weight"] == pytest.approx(46.069, abs=0.02)
    assert e["values"]["hydrogen_bond_donors"] == 1
    assert e["values"]["hydrogen_bond_acceptors"] == 1
    assert e["clinical_validation"] is False
    assert "safety_score" not in e["values"]
    assert "binding_affinity" not in e["values"]


def test_equivalent_smiles_have_same_canonical_evidence():
    from src.research_integrity import descriptor_evidence
    a, b = descriptor_evidence("CCO"), descriptor_evidence("OCC")
    assert a["canonical_smiles"] == b["canonical_smiles"]
    assert a["input_sha256"] == b["input_sha256"]
    assert a["values"] == b["values"]


@pytest.mark.parametrize("bad", ["", " ", "NOT_A_MOLECULE!!!", "C" * 4097, None, 42])
def test_invalid_smiles_produces_no_descriptor_evidence(bad):
    from src.research_integrity import descriptor_evidence
    with pytest.raises(ValueError):
        descriptor_evidence(bad)


def test_legacy_provider_metadata_does_not_verify_a_run():
    from src.research_integrity import report_document
    data = {"pathogen": "test", "top_candidates": [], "metadata": {"demo_mode": False, "models_used": ["Boltz-2", "Qwen3"], "llm_insights": {"executive_summary": "safe and effective"}}}
    md, export = report_document(data, simulated=False)
    result = json.loads(export)
    assert result["evidence_status"] == "unverified_legacy_output"
    assert result["clinical_validation"] is False
    assert "safe and effective" not in md
    assert "Production" not in md
    assert "LIVE" not in md


def test_simulation_remains_simulated_in_export():
    from src.research_integrity import report_document
    md, export = report_document({"pathogen": "test", "candidates": [{"drug": "fixture", "binding": .95}]}, simulated=True)
    data = json.loads(export)
    assert data["evidence_status"] == "simulated"
    assert data["provider_inference_verified"] is False
    assert "SIMULATED" in md


def test_report_does_not_mutate_original_or_promote_legacy_scores():
    from src.research_integrity import report_document
    original = {"pathogen": "test", "metadata": {}, "top_candidates": [{"drug_name": "test", "binding_affinity": .9}]}
    saved = json.dumps(original)
    md, exported = report_document(original, simulated=False)
    assert json.dumps(original) == saved
    assert "Strong binder" not in md
    assert json.loads(exported)["raw_results"] == original


def test_failure_has_no_fake_candidates_or_live_success():
    from src.research_integrity import error_document
    md, raw = error_document("pipeline_failed")
    data = json.loads(raw)
    assert data["status"] == "failed"
    assert data["raw_results"] is None
    assert "simulated" not in md.lower()


def test_provider_structure_metrics_do_not_imply_affinity():
    from src.research_integrity import binding_document
    from types import SimpleNamespace
    result = SimpleNamespace(success=True, confidence_score=.9, ptm_score=.8, iptm_score=.7,
                             ligand_iptm_score=.6, complex_plddt=85., complex_iplddt=80., raw_affinities={})
    md = binding_document(result)
    assert "0.9" in md
    assert "85" in md
    assert "Strong binder" not in md
    assert "not measured binding affinity" in md


@pytest.mark.parametrize("score", [float('nan'), float('inf'), -1., 1.1, True])
def test_malformed_provider_confidence_rejected(score):
    from src.research_integrity import binding_document
    from types import SimpleNamespace
    with pytest.raises(ValueError):
        binding_document(SimpleNamespace(success=True, confidence_score=score, complex_plddt=.8, iptm_score=.7, raw_affinities={}))
