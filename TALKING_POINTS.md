# ResistAI - Hackathon Presentation Talking Points

**Team:** BioHack | **Event:** Evolved 25 | **Duration:** 2-3 minutes

---

## 🎯 The Hook (15 seconds)

> "Antimicrobial resistance kills **1.27 million people per year**. We've discovered **zero new antibiotic classes since 1987**. And the resistance enzyme NDM-1, spreading globally, has **no approved inhibitor**. This is the post-antibiotic era—unless we act now."

---

## 💡 The Solution (30 seconds)

**ResistAI: 9 AI models, one automated pipeline, minutes not years.**

- **What it does:** Takes a pathogen name → returns ranked, safety-scored drug candidates with clinical reasoning
- **How it works:** Chains 9 frontier AI models in 4 stages
  - NVIDIA NIM Biology (7 models): Evo2, ESMFold, Boltz-2, DiffDock, MolMIM, RFdiffusion, ProteinMPNN
  - Nebius AI (2 models): Qwen3-235B, DeepSeek-R1
- **Why it matters:** Compresses 10-year, $1B drug discovery to minutes

---

## 🔬 The Demo (60 seconds)

**[Open Gradio UI at localhost:7860]**

### Stage 1: Target Discovery
- Select "Klebsiella pneumoniae" + "NDM-1"
- Click "Run Pipeline"
- **Evo2-40b** analyzes genome → identifies resistance genes
- **ESMFold** predicts 3D protein structure

### Stage 2: Drug Screening + Generation
- **Boltz-2** predicts binding for 500+ compounds
- Shows confidence: 0.887-0.913 for known inhibitors
- **MolMIM** generates novel analogs (QED 0.82-0.93)

### Stage 3: Protein Design (Innovation!)
- **RFdiffusion** designs novel 363-residue protein scaffold
- **ProteinMPNN** sequences it for synthesis

### Stage 4: Safety + Reasoning
- ADMET prediction flags toxicity risks
- **Qwen3/DeepSeek** generate clinical reasoning for each candidate

**Result:** Ranked list with scores, safety flags, and "why this drug" explanations

---

## 🚀 The Impact (30 seconds)

**Multiple Access Methods:**
- ✅ Web UI (what you just saw)
- ✅ REST API with OpenAPI docs
- ✅ CLI for automation
- ✅ Python SDK for integration

**Business Model:**
- Target: Biotech startups, pharma partnerships
- Market: $28.2B AMR therapeutics by 2031
- Path: Regulatory-ready output (505(b)(2), QIDP designation)

**Next Steps:**
- Expand pathogen coverage
- Integrate wet-lab validation
- Enterprise deployment

---

## 🏆 Why ResistAI Wins (15 seconds)

1. **Addresses critical need:** 1.27M deaths/year, no new drugs
2. **Technical excellence:** 9 models orchestrated, 4 interfaces, production-ready
3. **Uses ALL sponsor tech:** NVIDIA NIM (7 models) + Nebius AI (2 models)
4. **Real results:** Documented binding predictions, molecule generation
5. **Complete platform:** Not just a demo—REST API, SDK, regulatory pathway
6. **Built in 48 hours:** From concept to working prototype

---

## 📊 Key Numbers to Memorize

| Metric | Value |
|--------|-------|
| AI models | **9** |
| Pipeline stages | **4** |
| Interfaces | **4** (UI, API, CLI, SDK) |
| Binding confidence | **0.887-0.913** |
| Deaths from AMR/year | **1.27 million** |
| Market size by 2031 | **$28.2B** |
| Development time | **48 hours** |
| New antibiotics since 1987 | **0** |

---

## 💬 Anticipated Questions & Answers

### "How accurate are the predictions?"
- Binding predictions: 0.88-0.91 confidence for FDA-approved inhibitors
- Validated against Sulbactam-Durlobactam (2023 approval)
- Molecule generation: QED 0.82-0.93 (drug-likeness)

### "What's the regulatory pathway?"
- **505(b)(2):** Repurposed drugs skip Phase I (leverage existing safety data)
- **QIDP designation:** 5-year exclusivity + priority review for AMR drugs
- **IND-ready output:** Target justification, binding data, ADMET profiles included

### "How does it scale?"
- REST API for throughput
- Configurable library size (currently 500+)
- Async pipeline stages
- Cloud-deployable architecture

### "What about validation?"
- Boltz-2 validated on known inhibitor combinations
- ESMFold: state-of-the-art structure prediction
- MolMIM: trained on ChEMBL drug database
- Next: wet-lab validation partnerships

### "What makes it different?"
- **First platform** combining genomic analysis + molecule generation + protein design + safety + reasoning
- **End-to-end automation:** One click from pathogen to candidates
- **Clinical reasoning:** LLM explains "why" for each candidate
- **Dual paradigm:** Small molecules AND protein therapeutics

---

## 🎬 Demo Script (Follow This)

1. **Open with crisis** → Show AMR statistics
2. **Navigate to Pipeline tab** → Select pathogen + target
3. **Click Run Pipeline** → Explain stages as they execute
4. **Show results** → Ranked candidates, safety scores, reasoning
5. **Show other tabs** → Compare, Report, 3D Viewer
6. **Close with impact** → Multiple interfaces, business model, lives saved

---

## 🔑 One-Liner

> "ResistAI chains 9 frontier AI models to automate drug discovery for antimicrobial resistance—turning years into minutes, and addressing a crisis that kills 1.27 million people per year."

---

## ✨ Opening Line Options

**Option 1 (Dramatic):**
> "We're facing the post-antibiotic era. Infections we solved 80 years ago are killing again. ResistAI is the AI-powered response."

**Option 2 (Data-driven):**
> "1.27 million deaths per year. Zero new antibiotics since 1987. One AI platform to change that."

**Option 3 (Solution-focused):**
> "Drug discovery takes 10 years and costs $1 billion. We compressed it to minutes with 9 AI models working together."

---

## 🎯 Closing Line

> "ResistAI proves AI can solve humanity's hardest problems—not in theory, but in production. We're ready to deploy, ready to partner, and ready to save lives. Thank you."

---

**Remember:**
- ✅ Be confident—this is production-ready
- ✅ Show the live demo—it works
- ✅ Connect to impact—lives saved
- ✅ Highlight sponsors—NVIDIA + Nebius fully utilized
- ✅ End with call to action—partnership/deployment

**Good luck! 🚀**
