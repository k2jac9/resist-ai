"""Boltz response parsing must not accept an empty body as a successful prediction."""
import pytest


def parse(data):
    from src.models.nim.boltz2 import Boltz2Mixin
    class Client(Boltz2Mixin):
        def _post(self, endpoint, payload, timeout):
            assert endpoint == "boltz2"
            assert payload["ligands"] == [{"smiles":"CCO"}]
            return data
    return Client().predict_binding("MELPNIMHPVAK", "CCO")


@pytest.mark.parametrize("data", [{}, {"confidence_scores":[]}, {"confidence_scores":[float('nan')]},
                                  {"confidence_scores":[float('inf')]}, {"confidence_scores":[True]},
                                  {"confidence_scores":[1.1]}, {"confidence_scores":[-.1]},
                                  {"confidence_scores":"0.9"}, "error", {"confidence_scores":[.8],"ptm_scores":[2]}])
def test_invalid_response_is_not_success(data):
    result = parse(data)
    assert result.success is False


def test_zero_confidence_is_a_valid_observed_zero():
    result = parse({"confidence_scores":[0.0], "iptm_scores":[0.0]})
    assert result.success is True
    assert result.confidence_score == 0.0
    assert "confidence_score" in result.observed_fields
    assert "complex_plddt" not in result.observed_fields


def test_absent_metrics_are_not_presented_as_measured_zeros():
    from src.research_integrity import binding_document
    result = parse({"confidence_scores":[.8]})
    md = binding_document(result)
    assert "0.8" in md
    assert "Complex pLDDT" not in md


def test_provider_values_and_structure_are_preserved():
    result = parse({"confidence_scores":[.8], "complex_plddt_scores":[.9],
                    "output_files":[{"content":"example-cif"}], "affinities":{"raw":"uninterpreted"}, "_elapsed_ms":23})
    assert result.success is True
    assert result.complex_plddt == .9
    assert result.structure_cif == "example-cif"
    assert result.raw_affinities == {"raw":"uninterpreted"}
