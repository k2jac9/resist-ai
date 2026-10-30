"""UI callback tests. Legacy orchestration is an explicitly stubbed external boundary."""
import json
from types import SimpleNamespace
import pytest


def test_safety_returns_calculated_descriptors_without_random_verdict():
    from src.ui.tab_safety import analyze_safety
    plot, table, md = analyze_safety("CCO")
    assert plot is None and table is None
    assert "46.069" in md
    assert "RDKit" in md
    assert "PASS" not in md and "LIVE" not in md
    assert "not a safety prediction" in md


def test_safety_invalid_input_has_no_results():
    from src.ui.tab_safety import analyze_safety
    plot, table, md = analyze_safety("NOT_A_MOLECULE!!!")
    assert plot is None and table is None
    assert "unavailable" in md.lower()
    assert "Safety Score:" not in md


def test_models_fail_closed_without_provider(monkeypatch):
    from src.ui import tab_models
    monkeypatch.setattr(tab_models, "_nim", lambda: SimpleNamespace(available=False))
    payload, md = tab_models.predict_binding("MELPNIMHPVAK", "CCO")
    assert "unavailable" in md.lower()
    assert "confidence_score" not in md
    assert "random" not in md
    assert "MELPNIMHPVAK" in payload


def test_models_failure_never_falls_back_to_a_score(monkeypatch):
    from src.ui import tab_models
    def failed(*args):
        raise RuntimeError("secret-provider-response")
    monkeypatch.setattr(tab_models, "_nim", lambda: SimpleNamespace(available=True, predict_binding=failed))
    payload, md = tab_models.predict_binding("MELPNIMHPVAK", "CCO")
    assert "unavailable" in md.lower()
    assert "secret-provider-response" not in md
    assert "Strong binder" not in md


def test_models_show_structure_not_binding_verdict(monkeypatch):
    from src.ui import tab_models
    result = SimpleNamespace(success=True, confidence_score=.92, complex_plddt=85., iptm_score=.7)
    monkeypatch.setattr(tab_models, "_nim", lambda: SimpleNamespace(available=True, predict_binding=lambda *a: result))
    _, md = tab_models.predict_binding("MELPNIMHPVAK", "CCO")
    assert "0.92" in md and "85" in md
    assert "not measured binding affinity" in md


@pytest.mark.parametrize("seq,smiles", [("", "CCO"), ("DNA123", "CCO"), ("M" * 2001, "CCO"), ("MELPNIMHPVAK", "bad"), (None, "CCO")])
def test_invalid_model_input_never_reaches_provider(monkeypatch, seq, smiles):
    from src.ui import tab_models
    def forbidden():
        pytest.fail("Invalid input reached provider")
    monkeypatch.setattr(tab_models, "_nim", forbidden)
    _, md = tab_models.predict_binding(seq, smiles)
    assert "invalid" in md.lower()


def _configure_run(monkeypatch, *, fail=False):
    from src import research_execution as e
    calls = []
    monkeypatch.setattr(e, "_pathogen_key", lambda label: "test_pathogen")
    def run(key, n):
        calls.append((key, n))
        if fail:
            raise RuntimeError("private failure details")
        return {"pathogen": key, "targets": [], "top_candidates": [{"drug_name": "actual", "binding_affinity": .7}], "metadata": {"demo_mode": False}}
    monkeypatch.setattr(e, "_run_legacy", run)
    def demo(key, n):
        calls.append("fixture")
        return {"pathogen": key, "targets": [], "candidates": [{"drug_name": "fixture"}], "metadata": {"demo_mode": True}}
    monkeypatch.setattr(e, "_demo_inputs", demo)
    return calls


def test_live_report_exports_actual_returned_run_not_demo(monkeypatch):
    from src.ui.tab_report import generate_report
    calls = _configure_run(monkeypatch)
    md, raw = generate_report("test", 5, False)
    data = json.loads(raw)
    assert calls == [("test_pathogen", 5)]
    assert data["raw_results"]["top_candidates"][0]["drug_name"] == "actual"
    assert data["evidence_status"] == "unverified_legacy_output"
    assert "fixture" not in raw
    assert "3-5 years" not in md


def test_failed_live_report_does_not_silently_simulate(monkeypatch):
    from src.ui.tab_report import generate_report
    calls = _configure_run(monkeypatch, fail=True)
    md, raw = generate_report("test", 5, False)
    assert calls == [("test_pathogen", 5)]
    assert json.loads(raw)["status"] == "failed"
    assert "private failure details" not in md + raw


def test_demo_report_makes_no_pipeline_call(monkeypatch):
    from src.ui.tab_report import generate_report
    calls = _configure_run(monkeypatch)
    md, raw = generate_report("test", 5, True)
    assert calls == ["fixture"]
    assert json.loads(raw)["evidence_status"] == "simulated"
    assert "SIMULATED" in md


def test_failed_live_ui_clears_tables_and_has_no_fixture(monkeypatch):
    from src.ui.tab_pipeline import run_pipeline_ui
    calls = _configure_run(monkeypatch, fail=True)
    status, targets, hits, summary = run_pipeline_ui("test", 5, False)
    assert calls == [("test_pathogen", 5)]
    assert targets is None and hits is None
    assert "failed" in status.lower()
    assert "complete" not in status.lower()


@pytest.mark.parametrize("n,demo", [(0, True), (11, True), (-1, True), (True, True), (1.5, True), (5, "false")])
def test_invalid_run_controls_do_not_execute(monkeypatch, n, demo):
    from src.ui.tab_report import generate_report
    calls = _configure_run(monkeypatch)
    _, raw = generate_report("test", n, demo)
    assert not calls
    assert json.loads(raw)["status"] == "failed"


def test_legacy_client_exposes_config_not_live_success(monkeypatch):
    from src.models.llm_client import NebisLLM
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    llm = NebisLLM()
    assert llm.available is False
    assert llm.complete("test") == ""
    assert llm.last_error == "missing_api_key"
    assert llm.last_result is None


def test_legacy_client_uses_configured_model_in_actual_request(monkeypatch):
    from src.models.llm_client import NebisLLM
    from src.models.nebius_transport import NebiusTransport
    import httpx
    monkeypatch.setenv("NEBIUS_MODEL", "nvidia/test-model")
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    def handler(req):
        body = json.loads(req.content)
        assert body["model"] == "nvidia/test-model"
        return httpx.Response(200, json={"model": "nvidia/test-model", "choices": [{"finish_reason": "stop", "message": {"content": "{\"uncertainty\": \"unknown\"}"}}]})
    transport = NebiusTransport(client=httpx.Client(transport=httpx.MockTransport(handler)))
    llm = NebisLLM(transport=transport)
    assert llm.complete_json("test") == {"uncertainty": "unknown"}
    assert llm.last_result.model == "nvidia/test-model"


@pytest.mark.parametrize("bad", [None, {}, "not-a-list", [None], [42]])
def test_malformed_legacy_collections_fail_without_rendering(monkeypatch, bad):
    from src import research_execution as e
    from src.ui.tab_pipeline import run_pipeline_ui
    monkeypatch.setattr(e, "_run_legacy", lambda *args: {"targets": bad, "top_candidates": []})
    status, targets, candidates, _ = run_pipeline_ui("Klebsiella pneumoniae", 2, False)
    assert "failed" in status.lower()
    assert targets is None and candidates is None
