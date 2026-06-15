"""Tests for the model-explainability helpers."""
from src.models.schemas import ModelExplanation
from src.utils.explainability import (
    explain_boltz2_binding,
    generate_pipeline_explanations,
)


def test_generate_pipeline_explanations_covers_all_stages():
    explanations = generate_pipeline_explanations(
        drug_name="ResistX-1",
        target_name="NDM-1",
        binding_affinity=0.88,
        safety_score=0.75,
    )
    assert len(explanations) == 5
    assert all(isinstance(e, ModelExplanation) for e in explanations)
    assert all(e.reasoning_steps for e in explanations)
    names = " ".join(e.model_name for e in explanations)
    assert "Evo2" in names and "ESMFold" in names


def test_boltz2_explanation_reflects_inputs():
    exp = explain_boltz2_binding(
        drug_name="ResistX-1", target_name="NDM-1",
        binding_affinity=0.876, confidence=0.9,
    )
    assert isinstance(exp, ModelExplanation)
    assert "0.876" in exp.prediction
    assert exp.reasoning_steps
