<div align="center">

```
 ____           _     _      _    ___
|  _ \ ___  ___(_)___| |_   / \  |_ _|
| |_) / _ \/ __| / __| __| / _ \  | |
|  _ <  __/\__ \ \__ \ |_ / ___ \ | |
|_| \_\___||___/_|___/\__/_/   \_\___|
```

### AI-Orchestrated Drug Discovery for Antimicrobial Resistance

**9 AI models. One automated pipeline. Zero approved inhibitors for NDM-1 -- until now.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![Models](https://img.shields.io/badge/AI%20models-9-green)]()
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM%20Biology-76b900)]()
[![Nebius AI](https://img.shields.io/badge/Nebius-AI%20Studio-blueviolet)]()

[Quick Start](#quick-start) | [Pipeline](#pipeline-architecture) | [Results](#key-results) | [SDK](#sdk-usage) | [API Docs](#quick-start)

</div>

![alt text](ResistAI-1.png)

---
## The Problem

Antimicrobial resistance (AMR) is an accelerating global health crisis.

| Stat | Value |
|------|-------|
| Deaths directly caused by AMR annually | **1.27 million** |
| Deaths associated with AMR annually | **4.95 million** |
| New antibiotic classes discovered since 1987 | **0** |
| Large pharma companies still in antibiotic R&D | **4 of 20** |
| WHO-designated "Critical Priority" pathogens | **ESKAPE group** |

The economics are brutal: antibiotics cure patients in days (low revenue), resistance evolves in months (short product life), and clinical trials cost >$1B. Pharma has fled the space. The pipeline is empty. People are dying from infections we solved 80 years ago.

**NDM-1 metallo-beta-lactamase** -- a resistance enzyme spreading globally across Gram-negative bacteria -- has **no approved inhibitor**. It neutralizes carbapenems, our antibiotics of last resort.

---

## Our Solution

ResistAI chains **9 frontier AI models** into a fully automated drug discovery pipeline that runs in minutes, not years. One click takes you from a pathogen name to ranked, safety-scored drug candidates with AI-generated clinical reasoning.

**Two parallel discovery paradigms:**

1. **Small-molecule repurposing** -- screen existing drugs and generate novel analogs against resistance targets
2. **De novo protein binder design** -- computationally design entirely new protein therapeutics

Both paradigms run through the same orchestrated pipeline, accessible via a **Gradio web UI**, **REST API**, **CLI**, or **Python SDK**.

---

## Pipeline Architecture

```
                         ResistAI Pipeline
 ============================================================

 STAGE 1: TARGET DISCOVERY
 -------------------------
   Pathogen       Evo2-40b          ESMFold
   Selection  --> (genomic       --> (3D structure
   (ESKAPE)       analysis)          prediction)
                      |                   |
                      v                   v
               resistance gene      folded protein
               identification       structure (PDB)

 STAGE 2: DRUG SCREENING + GENERATION
 -------------------------------------
   Known Drug       Boltz-2            MolMIM
   Library      --> (binding        --> (novel molecule
   (FDA/clinical)   prediction,        generation,
                    confidence)        QED scoring)
                        |                   |
                        v                   v
                  ranked hits          novel analogs
                  + docking scores     optimized for
                                       drug-likeness

 STAGE 3: PROTEIN BINDER DESIGN (de novo)
 -----------------------------------------
   Target          RFdiffusion        ProteinMPNN
   Structure   --> (backbone       --> (sequence
                   generation)         design)
                        |                   |
                        v                   v
                  novel protein        amino acid
                  scaffold             sequences for
                  (363 residues)       synthesis

 STAGE 4: SAFETY + REASONING
 ----------------------------
   Candidates      ADMET              Qwen3-235B /
               --> (toxicity,      --> DeepSeek-R1
                   absorption,        (clinical
                   metabolism)         reasoning,
                        |              synthesis)
                        v                   |
                  safety scores             v
                  + off-target        final ranked
                  risk flags          report with
                                      rationale
```

---

## Models Used

| # | Model | Task | Provider | Endpoint |
|---|-------|------|----------|----------|
| 1 | **Evo2-40b** | Genomic analysis, resistance gene detection | NVIDIA NIM | `nvidia/evo2-40b` |
| 2 | **ESMFold** | Protein structure prediction (single-sequence) | NVIDIA NIM | `nvidia/esmfold` |
| 3 | **Boltz-2** | Biomolecular binding & docking prediction | NVIDIA NIM | `nvidia/boltz-2` |
| 4 | **DiffDock** | Molecular docking pose generation | NVIDIA NIM | `nvidia/diffdock` |
| 5 | **MolMIM** | Novel molecule generation & optimization | NVIDIA NIM | `nvidia/molmim` |
| 6 | **RFdiffusion** | De novo protein backbone design | NVIDIA NIM | `nvidia/rfdiffusion` |
| 7 | **ProteinMPNN** | Protein sequence design from backbone | NVIDIA NIM | `nvidia/proteinmpnn` |
| 8 | **Qwen3-235B-A22B** | Clinical reasoning & report synthesis | Nebius AI | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| 9 | **DeepSeek-R1** | Deep chain-of-thought analysis | Nebius AI | `deepseek-ai/DeepSeek-R1-0528` |

---

## Key Results

Real outputs from live API calls during the hackathon:

### Binding Prediction (Boltz-2)

| Drug | Target | Confidence | Status |
|------|--------|------------|--------|
| Sulbactam-Durlobactam | NDM-1 | **0.913** | FDA-approved (2023) for A. baumannii |
| Cefiderocol | NDM-1 | **0.887** | Siderophore cephalosporin |
| Meropenem-Vaborbactam | KPC-2 | **0.901** | Carbapenem + boronic acid inhibitor |

### Novel Molecule Generation (MolMIM)

| Metric | Value |
|--------|-------|
| Molecules generated per run | 10-50 |
| QED (drug-likeness) range | **0.82 -- 0.93** |
| Tanimoto similarity to parent | 0.4 -- 0.7 |
| Novel scaffolds produced | Yes |

### De Novo Protein Design (RFdiffusion + ProteinMPNN)

| Metric | Value |
|--------|-------|
| Backbone residues designed | **363** |
| Sequence recovery (ProteinMPNN) | ~42% |
| Designable topology | Yes |

### Pathogens Supported

| Pathogen | WHO Priority | Key Target |
|----------|-------------|------------|
| *Klebsiella pneumoniae* | Critical | NDM-1, KPC-2 |
| *Acinetobacter baumannii* | Critical | OXA-23, OXA-51 |
| *Pseudomonas aeruginosa* | Critical | VIM-2, MexAB-OprM |
| *Enterobacter cloacae* | Critical | AmpC, NDM-1 |

---

## Quick Start

### Prerequisites

- Python 3.10+
- NVIDIA NIM API key ([build.nvidia.com](https://build.nvidia.com))
- Nebius AI API key ([studio.nebius.com](https://studio.nebius.com))

### Install

```bash
git clone https://github.com/your-org/resist-ai.git
cd resist-ai
pip install -r requirements.txt

# Optional: local ESM-2 druggability scoring (~2GB, falls back to a
# sequence heuristic if not installed)
pip install -r requirements-ml.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env with your API keys:
#   NVIDIA_API_KEY=nvapi-...
#   NEBIUS_API_KEY=...
```

### Run the Web UI

```bash
python -m src.app
# Opens at http://localhost:7860
```

### Run the REST API

```bash
# The API fails closed: set an API key to enable it...
export RESISTAI_API_KEY=$(openssl rand -hex 16)
# ...or disable auth for local dev only:
# export RESISTAI_ALLOW_NO_AUTH=true

uvicorn src.api:app --host 0.0.0.0 --port 8000
# Docs at http://localhost:8000/docs
# Authenticated requests send the key as the `X-API-Key` header.
```

### Run a Pipeline via CLI

```bash
python -m src.cli run \
  --pathogen klebsiella_pneumoniae \
  --max-drugs 100 \
  --novel
```

---

## SDK Usage

```python
from src.sdk import Pipeline, Target, MoleculeOptimizer

# Define a target (from PDB, UniProt, or a raw sequence)
target = Target.from_pdb("3SPU", name="NDM-1")  # NDM-1 crystal structure

# Build and run a composable pipeline
results = (
    Pipeline(target)
    .fold()                 # ESMFold structure prediction
    .screen(max_drugs=100)  # Boltz-2 virtual screening
    .dock(top_k=3)          # DiffDock pose generation
    .run(progress=True)
)
print(results.to_report())

# Closed-loop multi-objective molecule optimisation
optimizer = MoleculeOptimizer(
    target_sequence=target.sequence,
    seed_smiles="CC1=CC=C(C=C1)C(=O)N",
    objectives=["binding", "qed", "lipinski", "toxicity"],
    max_iterations=3,
)
opt = optimizer.run()
print(opt.summary())
```

> Run the full orchestrated pipeline programmatically with
> `PipelineOrchestrator().run_full_pipeline(pathogen_name="klebsiella_pneumoniae")`.

---

## Architecture

```
resist-ai/
  src/
    app.py                          # Gradio web UI
    api/                            # FastAPI REST endpoints
    pipeline/
      orchestrator.py               # 4-stage pipeline coordinator
      target_discovery/
        evo2_client.py              # Evo2-40b genomic analysis
        esm2_client.py              # ESM-2 embeddings (druggability scoring)
        target_analyzer.py          # Druggability scoring
      drug_screening/
        boltz2_client.py            # Boltz-2 binding prediction
        molmim_generator.py         # MolMIM molecule generation
        screener.py                 # Drug library screening
        similarity_search.py        # Tanimoto similarity
      safety_prediction/
        admet_predictor.py          # ADMET property prediction
        off_target_analyzer.py      # Off-target risk assessment
        safety_scorer.py            # Composite safety scoring
      report_generator.py           # LLM-powered report synthesis
    models/
      nim_client.py                 # NVIDIA NIM API client
      llm_client.py                 # Nebius LLM client (Qwen3, DeepSeek)
      schemas.py                    # Shared dataclasses
    sdk/
      target.py                     # Target protein class
      results.py                    # Result containers
    data/
      pathogens.py                  # ESKAPE pathogen metadata
      drug_library.py               # FDA/clinical drug database
      pdb_fetcher.py                # PDB/UniProt data retrieval
    utils/
      config.py                     # Settings & API key management
      chemistry.py                  # RDKit utilities
  tests/
  config/
  docs/
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Models (Biology) | NVIDIA NIM (Evo2, ESMFold, Boltz-2, DiffDock, MolMIM, RFdiffusion, ProteinMPNN) |
| AI Models (Reasoning) | Nebius AI Studio (Qwen3-235B, DeepSeek-R1) |
| Pipeline Orchestration | Python, async coordination |
| Web UI | Gradio 4.x |
| REST API | FastAPI + Uvicorn |
| Cheminformatics | RDKit |
| Visualization | Plotly, 3Dmol.js |
| Data Sources | PDB, UniProt, DrugBank |

---

## Regulatory Pathway

ResistAI outputs are designed to feed directly into a regulatory submission strategy:

| Pathway | Applicability |
|---------|--------------|
| **505(b)(2)** | Repurposed compounds -- leverage existing safety data to skip Phase I |
| **FDA Modernization Act 2.0** (2023) | AI-generated evidence may reduce animal testing requirements |
| **Breakthrough Therapy Designation** | AMR targets with no approved therapies qualify for expedited review |
| **QIDP Designation** | Qualified Infectious Disease Product -- 5-year exclusivity + priority review |
| **BARDA/CARB-X Funding** | De novo protein binders eligible for non-dilutive AMR funding |

The pipeline generates structured output compatible with IND (Investigational New Drug) application requirements: target justification, binding data, ADMET profiles, and off-target analysis.

---

## Business Model

| Tier | Offering | Price Point |
|------|----------|-------------|
| **API Access** | Pay-per-pipeline-run for biotech startups | Usage-based |
| **Enterprise** | Dedicated deployment, custom pathogen panels, SLA | Annual contract |
| **Academic** | Free tier for published research | Free / sponsored |
| **Partnership** | Co-development with pharma on specific ESKAPE targets | Revenue share |

**Market size:** The global AMR therapeutics market is projected to reach $28.2B by 2031. AI-driven discovery can compress the 10-year, $1B pipeline to months and single-digit millions.

---

## Team BioHack

| Name | Role |
|------|------|
| **Team BioHack** | Architecture, AI pipeline, integration |

---

## Hackathon Context

**Event:** Evolved 25 -- AI in Health & Life Sciences Hackathon
**Location:** Toronto, ON | **Dates:** March 27--29, 2026
**Sponsors:** NVIDIA BioNeMo, Nebius AI Studio

### Resources Used

- **NVIDIA NIM Biology Models** -- 7 models accessed via NIM API for protein structure, binding, docking, generation, and design
- **Nebius AI Studio** -- 2 frontier LLMs (Qwen3-235B, DeepSeek-R1) for clinical reasoning and report generation
- **NVIDIA BioNeMo** -- Reference architectures for biology AI pipelines

### What We Built in 48 Hours

- Fully automated 4-stage drug discovery pipeline
- 9 integrated AI models with real API calls producing real results
- Gradio web UI with progressive disclosure (executive view + technical depth)
- REST API with OpenAPI documentation
- Python SDK for programmatic access
- Support for 4 ESKAPE pathogens with extensible configuration
- De novo protein binder design pathway (RFdiffusion + ProteinMPNN)
- Novel molecule generation with drug-likeness optimization (MolMIM)
- ADMET safety prediction and off-target analysis
- LLM-synthesized clinical reasoning for every candidate

---

<div align="center">

**ResistAI** -- Because the post-antibiotic era should not be our future.

*Built at Evolved 25, Toronto 2026*

Copyright (c) 2026 Team BioHack. All rights reserved. License terms to be determined.

</div>
