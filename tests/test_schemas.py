"""Regression tests for src.models.schemas serialization round-trips.

Guards against a copy-paste regression where PipelineResults.from_dict was
defined inside the RegulatoryReport class, leaving RegulatoryReport.from_dict
shadowed and PipelineResults.from_dict missing.
"""
from src.models.schemas import (
    PipelineResults,
    RegulatoryPathway,
    RegulatoryReport,
    TargetResult,
    USPMonographInfo,
)


def test_pipeline_results_round_trip():
    pr = PipelineResults(
        pathogen="klebsiella_pneumoniae",
        targets=[TargetResult(name="NDM-1", pdb_code="3SPU")],
        metadata={"demo_mode": True},
    )
    restored = PipelineResults.from_dict(pr.to_dict())
    assert isinstance(restored, PipelineResults)
    assert restored.pathogen == "klebsiella_pneumoniae"
    assert len(restored.targets) == 1
    assert restored.targets[0].name == "NDM-1"
    assert restored.metadata == {"demo_mode": True}


def test_pipeline_results_str():
    pr = PipelineResults(pathogen="staphylococcus_aureus")
    assert "PipelineResults(staphylococcus_aureus" in str(pr)


def test_regulatory_report_from_dict_returns_regulatory_report():
    report = RegulatoryReport(
        drug_name="Meropenem",
        smiles="CC(O)=O",
        target_name="NDM-1",
        pathway=RegulatoryPathway(
            pathway_type="505(b)(2)",
            timeline_years=(2.0, 4.0),
            cost_estimate_usd=(1_000_000, 5_000_000),
            success_rate=0.4,
        ),
        usp_info=USPMonographInfo(drug_name="Meropenem"),
        qidp_eligible=True,
    )
    restored = RegulatoryReport.from_dict(report.to_dict())
    assert isinstance(restored, RegulatoryReport)
    assert restored.drug_name == "Meropenem"
    assert restored.qidp_eligible is True
    assert restored.pathway.pathway_type == "505(b)(2)"
    assert restored.usp_info.drug_name == "Meropenem"
