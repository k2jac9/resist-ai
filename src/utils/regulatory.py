"""Regulatory intelligence utilities for FDA pathway prediction and timeline calculation."""

from __future__ import annotations

from typing import Any

from ..models.schemas import (
    DrugCandidate,
    ModelExplanation,
    RegulatoryPathway,
    RegulatoryReport,
    USPMonographInfo,
)

# USP Monograph database (subset - in production this would be a full database)
USP_MONOGRAPH_DB = {
    "Meropenem": {"has_monograph": True, "monograph_id": "USP42-NF37", "category": "API", "generic": True},
    "Imipenem": {"has_monograph": True, "monograph_id": "USP42-NF37", "category": "API", "generic": True},
    "Colistin": {"has_monograph": True, "monograph_id": "USP42-NF37", "category": "API", "generic": True},
    "Tigecycline": {"has_monograph": True, "monograph_id": "USP43-NF38", "category": "API", "generic": True},
    "Cefiderocol": {"has_monograph": False, "monograph_id": "", "category": "", "generic": False},
    "Aztreonam": {"has_monograph": True, "monograph_id": "USP42-NF37", "category": "API", "generic": True},
    "Avibactam": {"has_monograph": True, "monograph_id": "USP43-NF38", "category": "API", "generic": False},
    "Vaborbactam": {"has_monograph": False, "monograph_id": "", "category": "", "generic": False},
    "Ceftazidime": {"has_monograph": True, "monograph_id": "USP42-NF37", "category": "API", "generic": True},
    "Relebactam": {"has_monograph": False, "monograph_id": "", "category": "", "generic": False},
}

# Regulatory pathway definitions
PATHWAY_DEFINITIONS = {
    "505(b)(2)": {
        "name": "505(b)(2) Drug Repurposing",
        "timeline_years": (3, 8),
        "cost_usd": (200_000_000, 600_000_000),
        "success_rate": 0.17,
        "description": "Accelerated pathway for drugs with existing safety data",
        "requirements": [
            "Reference listed drug (RLD) exists",
            "Leverages existing pharmacology, safety, or efficacy data",
            "New indication, dosage form, or formulation"
        ]
    },
    "505(b)(1)": {
        "name": "505(b)(1) De Novo NDA",
        "timeline_years": (10, 17),
        "cost_usd": (1_000_000_000, 2_000_000_000),
        "success_rate": 0.10,
        "description": "Full new drug application for novel molecules",
        "requirements": [
            "Complete preclinical safety and efficacy studies",
            "Phase 1, 2, and 3 clinical trials",
            "Demonstrates safety and efficacy independently"
        ]
    },
    "BLA": {
        "name": "Biologics License Application",
        "timeline_years": (10, 15),
        "cost_usd": (1_000_000_000, 2_500_000_000),
        "success_rate": 0.08,
        "description": "Pathway for biological therapeutic products",
        "requirements": [
            "Characterization of biological product",
            "Manufacturing process validation",
            "Clinical efficacy and safety demonstration"
        ]
    },
    "OTC_Monograph": {
        "name": "OTC Monograph Pathway",
        "timeline_years": (0.25, 1),
        "cost_usd": (50_000, 500_000),
        "success_rate": 0.95,
        "description": "Fastest pathway for monograph-conforming OTC products",
        "requirements": [
            "Product conforms to existing OTC monograph",
            "Generally recognized as safe and effective (GRASE)",
            "No pre-market approval required"
        ]
    }
}

# FDA accelerated programs
ACCELERATED_PROGRAMS = {
    "QIDP": {
        "name": "Qualified Infectious Disease Product",
        "benefit": "5-year market exclusivity extension + Fast Track + Priority Review",
        "eligibility": "Treats serious/life-threatening infections (ESKAPE pathogens)",
        "timeline_reduction": 0.4  # 40% faster
    },
    "Fast_Track": {
        "name": "Fast Track Designation",
        "benefit": "Rolling review + more frequent FDA meetings",
        "eligibility": "Addresses unmet medical need for serious condition",
        "timeline_reduction": 0.2
    },
    "Breakthrough": {
        "name": "Breakthrough Therapy",
        "benefit": "Intensive FDA guidance + organizational commitment",
        "eligibility": "Preliminary evidence of substantial improvement",
        "timeline_reduction": 0.3
    },
    "Orphan": {
        "name": "Orphan Drug Designation",
        "benefit": "7-year market exclusivity + tax credits + grant funding",
        "eligibility": "Treats rare disease (<200,000 US patients)",
        "timeline_reduction": 0.15
    }
}


def get_usp_monograph_info(drug_name: str) -> USPMonographInfo:
    """Retrieve USP monograph information for a drug."""
    info = USP_MONOGRAPH_DB.get(drug_name, {})
    return USPMonographInfo(
        drug_name=drug_name,
        has_monograph=info.get("has_monograph", False),
        monograph_id=info.get("monograph_id", ""),
        usp_category=info.get("category", ""),
        generic_available=info.get("generic", False),
        last_updated="2025"
    )


def predict_regulatory_pathway(
    drug_name: str,
    is_novel_molecule: bool = False,
    is_biologic: bool = False,
    has_clinical_data: bool = False,
) -> RegulatoryPathway:
    """Predict the most appropriate FDA regulatory pathway."""

    usp_info = get_usp_monograph_info(drug_name)

    # Determine pathway
    if is_biologic:
        pathway_key = "BLA"
    elif is_novel_molecule:
        pathway_key = "505(b)(1)"
    elif usp_info.has_monograph and usp_info.generic_available:
        # Could potentially use OTC monograph if GRASE
        # For AMR, likely 505(b)(2)
        pathway_key = "505(b)(2)"
    elif has_clinical_data:
        pathway_key = "505(b)(2)"
    else:
        pathway_key = "505(b)(1)"

    pathway_def = PATHWAY_DEFINITIONS[pathway_key]

    return RegulatoryPathway(
        pathway_type=pathway_key,
        timeline_years=pathway_def["timeline_years"],
        cost_estimate_usd=pathway_def["cost_usd"],
        success_rate=pathway_def["success_rate"],
        eligibility_criteria=pathway_def["requirements"],
        accelerated_options=_get_accelerated_options(pathway_key)
    )


def _get_accelerated_options(pathway_key: str) -> list[str]:
    """Get available accelerated program options for a pathway."""
    options = []

    # QIDP always available for antibiotics
    options.append("QIDP (Qualified Infectious Disease Product)")

    if pathway_key in ["505(b)(1)", "505(b)(2)"]:
        options.append("Fast Track Designation")
        options.append("Breakthrough Therapy Designation")

    if pathway_key == "BLA":
        options.append("Breakthrough Therapy Designation")

    return options


def calculate_timeline_with_accelerations(
    base_pathway: RegulatoryPathway,
    qidp: bool = False,
    fast_track: bool = False,
    breakthrough: bool = False,
    orphan: bool = False
) -> dict[str, Any]:
    """Calculate adjusted timeline based on accelerated program eligibility."""

    min_years, max_years = base_pathway.timeline_years
    reduction_factor = 1.0

    programs_applied = []

    if qidp:
        reduction_factor *= (1 - ACCELERATED_PROGRAMS["QIDP"]["timeline_reduction"])
        programs_applied.append("QIDP")

    if fast_track:
        reduction_factor *= (1 - ACCELERATED_PROGRAMS["Fast_Track"]["timeline_reduction"])
        programs_applied.append("Fast Track")

    if breakthrough:
        reduction_factor *= (1 - ACCELERATED_PROGRAMS["Breakthrough"]["timeline_reduction"])
        programs_applied.append("Breakthrough")

    if orphan:
        reduction_factor *= (1 - ACCELERATED_PROGRAMS["Orphan"]["timeline_reduction"])
        programs_applied.append("Orphan Drug")

    adjusted_min = round(min_years * reduction_factor, 1)
    adjusted_max = round(max_years * reduction_factor, 1)

    return {
        "base_timeline": (min_years, max_years),
        "accelerated_timeline": (adjusted_min, adjusted_max),
        "programs_applied": programs_applied,
        "time_saved_years": round((min_years - adjusted_min + max_years - adjusted_max) / 2, 1),
        "acceleration_factor": round((1 - reduction_factor) * 100, 1)  # percentage
    }


def generate_regulatory_report(
    candidate: DrugCandidate,
    model_explanations: list[ModelExplanation] | None = None
) -> RegulatoryReport:
    """Generate a comprehensive regulatory intelligence report for a drug candidate."""

    # Determine if novel molecule or repurposing
    usp_info = get_usp_monograph_info(candidate.drug_name)
    is_novel = not usp_info.has_monograph
    is_biologic = "protein" in candidate.drug_name.lower() or "binder" in candidate.drug_name.lower()

    # Predict pathway
    pathway = predict_regulatory_pathway(
        candidate.drug_name,
        is_novel_molecule=is_novel,
        is_biologic=is_biologic,
        has_clinical_data=usp_info.generic_available
    )

    # Determine accelerated program eligibility
    # For AMR targeting ESKAPE pathogens, QIDP is almost always eligible
    qidp_eligible = True  # Antibiotics for serious infections
    fast_track_eligible = True  # Unmet medical need (AMR)
    breakthrough_eligible = candidate.overall_score > 0.8  # Strong preliminary data
    orphan_eligible = False  # AMR typically not rare (<200k patients)

    return RegulatoryReport(
        drug_name=candidate.drug_name,
        smiles=candidate.smiles,
        target_name=candidate.target_name,
        pathway=pathway,
        usp_info=usp_info,
        qidp_eligible=qidp_eligible,
        orphan_eligible=orphan_eligible,
        fast_track_eligible=fast_track_eligible,
        breakthrough_eligible=breakthrough_eligible,
        model_explanations=model_explanations or []
    )


def generate_preind_briefing_document(report: RegulatoryReport) -> str:
    """Generate a pre-IND briefing document template."""

    pathway_def = PATHWAY_DEFINITIONS.get(report.pathway.pathway_type, {})

    doc = f"""
# PRE-IND BRIEFING DOCUMENT

## Drug Candidate Information

**Drug Name:** {report.drug_name}
**SMILES:** `{report.smiles}`
**Target:** {report.target_name}
**Therapeutic Area:** Antimicrobial Resistance (AMR)

---

## Regulatory Strategy

### Proposed Pathway
**{pathway_def.get('name', report.pathway.pathway_type)}**

{pathway_def.get('description', '')}

**Estimated Timeline:** {report.pathway.timeline_years[0]:.1f} - {report.pathway.timeline_years[1]:.1f} years
**Estimated Cost:** ${report.pathway.cost_estimate_usd[0]:,} - ${report.pathway.cost_estimate_usd[1]:,} USD
**Historical Success Rate:** {report.pathway.success_rate * 100:.1f}%

### Eligibility Criteria
"""

    for criterion in report.pathway.eligibility_criteria:
        doc += f"- {criterion}\n"

    doc += "\n---\n\n## USP Monograph Status\n\n"

    if report.usp_info.has_monograph:
        doc += f"""
**Status:** ✅ USP Monograph Exists
**Monograph ID:** {report.usp_info.monograph_id}
**Category:** {report.usp_info.usp_category}
**Generic Available:** {'Yes' if report.usp_info.generic_available else 'No'}

**Impact:** Existing USP monograph supports 505(b)(2) pathway eligibility.
Prior safety and pharmacology data can be referenced, potentially reducing
preclinical requirements by ~40%.
"""
    else:
        doc += """
**Status:** ⚠️ No USP Monograph

**Impact:** Requires full characterization and quality standards development.
USP monograph will be created post-approval. Recommend early engagement with
USP's Pharmaceutical Development & Innovation team.
"""

    doc += "\n---\n\n## Accelerated Program Opportunities\n\n"

    if report.qidp_eligible:
        doc += """### ✅ QIDP (Qualified Infectious Disease Product)
**Eligibility:** High - Targets ESKAPE pathogen serious/life-threatening infection
**Benefits:**
- 5-year market exclusivity extension
- Fast Track designation (automatic)
- Priority Review (automatic)
- Wildcard pediatric voucher eligibility (~$100M+ value)

**Action:** Submit QIDP designation request concurrent with Pre-IND meeting request
"""

    if report.fast_track_eligible:
        doc += """
### ✅ Fast Track Designation
**Eligibility:** High - Addresses unmet medical need for AMR
**Benefits:**
- Rolling submission (accelerates review start)
- More frequent FDA communication
- ~20% timeline reduction

**Action:** Request during End-of-Phase 2 meeting
"""

    if report.breakthrough_eligible:
        doc += """
### ✅ Breakthrough Therapy Designation
**Eligibility:** Moderate-High (conditional on strong Phase 1/2 data)
**Benefits:**
- Intensive FDA guidance (organizational commitment)
- Potential for surrogate endpoints
- ~30% timeline reduction

**Action:** Request after preliminary clinical evidence of substantial improvement
"""

    doc += "\n---\n\n## AI Model Transparency\n\n"

    if report.model_explanations:
        doc += "Per FDA 2025 draft guidance on AI in drug development, the following model explanations support this candidate:\n\n"
        for i, expl in enumerate(report.model_explanations, 1):
            doc += f"### {i}. {expl.model_name}\n"
            doc += f"**Prediction:** {expl.prediction}  \n"
            doc += f"**Confidence:** {expl.confidence * 100:.1f}%  \n\n"

            if expl.reasoning_steps:
                doc += "**Reasoning:**\n"
                for step in expl.reasoning_steps:
                    doc += f"- {step}\n"
                doc += "\n"

            if expl.feature_importance:
                doc += "**Key Features:**\n"
                for feature, importance in sorted(expl.feature_importance.items(),
                                                 key=lambda x: x[1], reverse=True)[:5]:
                    doc += f"- {feature}: {importance:.3f}\n"
                doc += "\n"
    else:
        doc += "_Model explanations will be added from pipeline results._\n\n"

    doc += """
---

## Recommended Next Steps

1. **Pre-IND Meeting Request**
   - Submit FDA Form 3674 (Type B meeting)
   - Target: Q2 2026
   - Focus areas: Pathway confirmation, CMC strategy, clinical trial design

2. **QIDP Designation Request**
   - Concurrent with Pre-IND meeting request
   - Include evidence of serious/life-threatening infection treatment

3. **Preclinical Package Completion**
   - GLP toxicology studies (if 505(b)(1))
   - Pharmacokinetics/pharmacodynamics (PK/PD)
   - Safety pharmacology

4. **CMC Development**
   - API synthesis scale-up
   - Analytical method development
   - Stability studies

5. **Clinical Trial Site Identification**
   - Engage infectious disease research networks
   - Identify AMR patient populations

---

**Document Generated:** {report.pathway.timeline_years}
**ResistAI Platform:** AI-Orchestrated Drug Discovery for AMR
"""

    return doc
