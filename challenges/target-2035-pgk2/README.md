# DREAM x CACHE — Target 2035 Drug Discovery Challenge (PGK2)

> **Status:** Research / participation brief. This is a **standalone subproject** —
> it documents the challenge and what is needed to enter. It does **not** modify the
> core ResistAI pipeline and contains no challenge code or data.
>
> **Compiled:** June 2026 from the challenge announcement, the CACHE challenge site,
> and SGC / Target 2035 public materials. **Fact-checked 2026-06-18** against
> [cache-challenge.org](https://cache-challenge.org/critical-assessment-computational-hit-finding-experiments)
> and the challenge announcement — the previously-flagged items (dates, selectivity
> residues, Synapse ID) are now **confirmed** (see the fact-check log at the bottom).
> A deeper companion dossier lives in [`RESEARCH.md`](./RESEARCH.md).
>
> **Two distinct challenges share the PGK2 target — don't conflate them:**
> this brief is about the **Second Target 2035 DEL-ML Challenge** (the *computational*
> "DREAM × CACHE Target 2035" challenge, Synapse `syn75349604`), **not** **CACHE
> Challenge #7** (a separate *wet-lab* CACHE challenge that ran Aug 12 – Oct 10, 2025
> and generated much of the experimental data this one trains on).

---

## TL;DR — what this is and what it would take to enter

- **What:** A DEL-ML (DNA-encoded-library + machine-learning) challenge to predict
  small molecules that **bind phosphoglycerate kinase 2 (PGK2)** — a sperm-motility
  enzyme and a promising **non-hormonal contraception** target.
- **Phase 1 (retrospective, free):** Train ML models on a **~890M-compound** DEL
  screen (SMILES + read counts + building-block compositions), then **retrieve the
  ~450 confirmed true positives** hidden inside a 400K-compound ASMS test set. The
  retrospective phase includes an **active-learning** round.
- **Phase 2 (prospective, top 10 only):** Predict novel hits from the **Enamine**
  catalog; each finalist buys **50 in-stock compounds (< $1,000)**, organizers cover
  all experimental testing.
- **To enter you need:** a free **Synapse** account, to register for the challenge
  project, to download the DEL training data + ASMS test set, and to submit a ranked
  prediction file before the deadline. **Registration is a manual step you must do
  under your own Synapse account** (see [How to participate](#how-to-participate)).

---

## The science

| Item | Detail |
|------|--------|
| **Target** | Phosphoglycerate kinase 2 (**PGK2**) |
| **Biology** | Enzyme essential for **sperm motility / bioenergetics**; expressed in meiotic & post-meiotic spermatogenic cells |
| **Why it matters** | Promising target for **non-hormonal male contraception** (aligned with the Gates Foundation non-hormonal contraceptive program) |
| **Key difficulty** | **Selectivity over PGK1**, the ubiquitous glycolytic homologue. ✅ **Confirmed** against cache-challenge.org: the binding pocket differs at two positions — **242: Tyr (PGK2) vs Phe (PGK1)** and **255: Ala (PGK2) vs Thr (PGK1)**. (CACHE #7 additionally excludes the **quinazoline** scaffold; confirm whether that constraint carries into the DEL-ML challenge.) |
| **Structures** | Mouse **PGK2** has apo + substrate-bound crystal structures in the PDB (**2P9Q**, **2P9T**, **2PAA**); human **PGK1** has many structures — both usable for homology / selectivity modeling. Note: the two active sites are otherwise *highly* similar, which is exactly why selectivity is hard. |

## Organizers

Part of the **Target 2035** initiative (SGC's open-science effort to develop a
pharmacological modulator for **every human protein by 2035**). This is the
**Second** Target 2035 DEL-ML challenge — the successor to the inaugural *First DREAM
Target 2035 Drug Discovery Challenge* (Synapse `syn65660836`, 2025) — and is run by:

- **The Structural Genomics Consortium (SGC)**
- Lab of **Damian Young** — Baylor College of Medicine
- Lab of **Neelagandan Kamariah** — InStem
- **IBM (DREAM)** and **Sage Bionetworks** (Synapse platform + scoring infrastructure)
- Network / logistical support: **Conscience**, **BEACON**, and **MAINFRAME**
  (international ML + comp-chem network providing curated data and experimental feedback)

All data and results are shared **openly and publicly** (DEL data is released via the
ML-ready **AIRCHECK** platform).

---

## Data provided

| Dataset | Size | Role |
|---------|------|------|
| **DEL screen** (DNA-encoded library) | ~**890M SMILES** with read counts + building-block compositions (PGK2 binding signal) | **Training** set for ML models |
| **ASMS screen** (affinity-selection mass spec) | **400K** compounds containing **~450 confirmed true positives** | **Retrospective test** set — the *hidden hits* you must retrieve |
| **Enamine catalog** | In-stock catalog | **Prospective** prediction source (Phase 2 only) |

> DEL data is noisy and structured (building-block / synthon encodings, enrichment
> counts). Plan for DEL-specific denoising and the DEL→ASMS **domain shift** between
> train and test.

---

## Phases, scoring & costs

### Phase 1 — Retrospective (free, open to all)
- Train on the DEL data; submit a **ranked list** that recovers the hidden confirmed
  hits inside the 400K ASMS set.
- **Goal / scoring:** retrieve the **most diverse set of hidden hits** (diversity of
  recovered chemical series matters, not just raw count).

### Phase 2 — Prospective (top 10 from Phase 1)
- Predict **novel** hits from the Enamine catalog; finalists procure **50 compounds
  (< $1,000 total)**; organizers fund 100% of experimental testing.
- **Winning criteria:** (1) number of **novel chemical series** identified from the
  test set, and (2) **overall number of hits** confirmed in the prospective phase.

### Costs / equity
- Phase 1: **free**.
- Phase 2: ~**< $1,000** in compounds per finalist; testing covered by organizers.
- **MAINFRAME** participants from **low/medium-income countries** advancing to Phase 2
  can have all expenses covered by the SGC.

---

## Key dates

> ✅ **Year confirmed: 2026.** The challenge was **announced ~June 16, 2026**, so the
> bare "Jul 7" / "Sep 15" dates are the **2026** cycle. Re-confirm exact times and any
> extensions on Synapse, but the year is no longer in doubt.

| Date | Event |
|------|-------|
| **Jul 7, 2026, 9am EDT / 3pm CEST** | Challenge launch **webinar** (Zoom; register to attend) |
| **Sep 15, 2026** | **First submission deadline** — retrospective phase |
| TBD | Top-10 invited to prospective (Enamine) phase |

> 📌 **Precedent for extensions:** the related CACHE #7 deadline was pushed from its
> original date to **Oct 10, 2025**, so a Sep 15 slip is plausible — watch Synapse.

---

## How to participate

1. **Create a free Synapse account** at <https://www.synapse.org> (Sage Bionetworks).
2. **Find the challenge project** — the Synapse project is
   `https://www.synapse.org/Synapse:syn75349604` ✅ (confirmed: title renders as
   *"DREAM × CACHE Target 2035 Drug Discovery Challenge"*; the page requires login).
3. **Register / join the challenge team** on the project's wiki and accept the data-use
   / challenge terms.
4. **Download the data**: DEL training set + ASMS retrospective test set.
5. **Build a model** and produce predictions in the **required submission format**
   (column order, ID scheme, ranking/score column — read the wiki's submission spec).
6. **Submit before the deadline** via the Synapse submission queue; check the
   leaderboard for scored feedback.
7. *(Optional)* **Attend the launch webinar** (Jul 7) for rules Q&A.

> ⚠️ **Registration is manual and account-bound.** It must be completed by you
> (alexcastellanos29@gmail.com) under your own Synapse credentials — it cannot be
> automated here. The steps above are the checklist to follow.

### Participation checklist
- [ ] Synapse account created
- [ ] Registered on the Target 2035 PGK2 challenge project
- [ ] Data-use terms accepted
- [ ] DEL training data downloaded
- [ ] ASMS retrospective test set downloaded
- [ ] Submission format / scoring spec read on the wiki
- [ ] Baseline model trained
- [ ] First submission made before the Sept 15 deadline
- [ ] (Webinar attended — Jul 7)

---

## How this relates to ResistAI (notes only — nothing wired up)

ResistAI targets **antimicrobial resistance** (NDM-1 / ESKAPE), so this PGK2 challenge
is a **different domain**. However, several existing components could be reused **if**
the team later decides to build a real entry (which would be a separate effort —
likely the *"working baseline model"* scope, not this research brief):

- `src/utils/chemistry.py` — RDKit utilities (fingerprints, descriptors)
- `src/pipeline/drug_screening/similarity_search.py` — Tanimoto similarity / diversity
  (directly relevant to the *"diverse hits"* scoring)
- `src/pipeline/drug_screening/molmim_generator.py` — generative chemistry (Phase 2)
- Boltz-2 / DiffDock clients — structure-based scoring for **PGK2-vs-PGK1 selectivity**

A real entry would still need **DEL-specific** data handling (synthon encodings,
enrichment-count denoising) and a **large-scale ML classifier**, which ResistAI does
not currently provide.

> 💡 **Free model stack:** a fully-free toolkit (NVIDIA NIM free tier — Boltz-2,
> DiffDock, MolMIM, GenMol — plus open-weights MoLFormer / Uni-Mol / ChemBERTa / ESM-2
> for the DEL ranking) is detailed in [`RESEARCH.md` §9](./RESEARCH.md#9-free--frontier-models-you-can-use-nvidia--open).
> Most of the NVIDIA half is **already integrated** in ResistAI.

---

## Fact-check log (2026-06-18)

| Item | Before | After verification | Source |
|------|--------|--------------------|--------|
| Year of dates | "appears 2026" | ✅ **2026** (announced ~Jun 16 2026) | challenge announcement |
| Selectivity residues | "verify these" | ✅ **Confirmed** 242 Tyr→Phe, 255 Ala→Thr | cache-challenge.org |
| DEL training size | "~1 billion" | ↳ **890M SMILES** (precise) | challenge announcement |
| ASMS test set | "400K, hidden hits" | ↳ 400K with **~450 true positives** | challenge announcement |
| Synapse synID | "verify current" | ✅ **syn75349604** confirmed | synapse.org |
| Challenge identity | one "DREAM x CACHE" | ↳ **Second DEL-ML challenge**, distinct from wet-lab **CACHE #7** | cache-challenge.org |

## Sources

- [CACHE — Critical Assessment of Computational Hit-finding Experiments (challenge list incl. PGK2 DEL-ML)](https://cache-challenge.org/critical-assessment-computational-hit-finding-experiments)
- [CACHE Challenge #7: selective PGK2 inhibitors — Conscience (dates, scope)](https://conscience.ca/event/cache7/)
- [Target 2035 — Structural Genomics Consortium](https://www.thesgc.org/target2035)
- ["Announcing the Second Target 2035 DEL-ML challenge" — M. Schapira (announcement)](https://www.linkedin.com/posts/matthieu-schapira-84312510_announcing-the-second-target-2035-del-ml-activity-7472639611945545731-aOeW)
- [First DREAM Target 2035 Drug Discovery Challenge — Synapse `syn65660836`](https://www.synapse.org/Synapse:syn65660836)
- [PGK2 essential for sperm function & male fertility (Danshina et al.) — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2802118/)
- [Mouse PGK2 crystal structure 2P9Q — RCSB PDB](https://www.rcsb.org/structure/2P9Q)
- [Pharos: PGK2 target page](https://pharos.nih.gov/targets/PGK2)
- Synapse challenge project (login required): `https://www.synapse.org/Synapse:syn75349604`
