# DREAM x CACHE — Target 2035 Drug Discovery Challenge (PGK2)

> **Status:** Research / participation brief. This is a **standalone subproject** —
> it documents the challenge and what is needed to enter. It does **not** modify the
> core ResistAI pipeline and contains no challenge code or data.
>
> **Compiled:** June 2026 from the challenge announcement, the CACHE challenge site,
> and SGC / Target 2035 public materials. Some figures (esp. dates and the exact
> selectivity residues) should be **re-verified on Synapse** before relying on them.

---

## TL;DR — what this is and what it would take to enter

- **What:** A DEL-ML (DNA-encoded-library + machine-learning) challenge to predict
  small molecules that **bind phosphoglycerate kinase 2 (PGK2)** — a sperm-motility
  enzyme and a promising **non-hormonal contraception** target.
- **Phase 1 (retrospective, free):** Train ML models on a ~1-billion-compound DEL
  screen, then **retrieve hidden confirmed hits** from a 400K-compound ASMS test set.
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
| **Key difficulty** | **Selectivity over PGK1**, the ubiquitous glycolytic homologue. The orthosteric pockets reportedly differ at only ~2 positions — *Y242 (PGK2) vs F242 (PGK1)* and *A255 (PGK2) vs T255 (PGK1)*. **Verify these residues against the official challenge spec before modeling.** |
| **Structures** | PGK1 has crystal structures in the PDB; usable as a homology/selectivity reference. |

## Organizers

Part of the **Target 2035** initiative (SGC's effort to find an open-science
pharmacological modulator for every human protein by 2035). This challenge is the
successor to the inaugural *DREAM Target 2035 Drug Discovery Challenge* and is run by:

- **The Structural Genomics Consortium (SGC)**
- Lab of **Damian Young** — Baylor College of Medicine
- Lab of **Neelagandan Kamariah** — InStem
- **IBM (DREAM)** and **Sage Bionetworks** (Synapse platform + scoring infrastructure)
- Logistical / technical support: **Conscience** and **BEACON**

All data and results are shared **openly and publicly**.

---

## Data provided

| Dataset | Size | Role |
|---------|------|------|
| **DEL screen** (DNA-encoded library) | ~**1 billion** compounds with PGK2 binding data | **Training** set for ML models |
| **ASMS screen** (affinity-selection mass spec) | **400K** compounds, hits confirmed in a **kinase assay** | **Retrospective test** set — contains the *hidden hits* you must retrieve |
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

> The announcement gave dates **without a year**. Given the June-2026 context and an
> upcoming **July 7** webinar, these appear to be the **2026** cycle — **confirm the
> exact year and deadlines on Synapse before planning around them.**

| Date | Event |
|------|-------|
| **Jul 7, 9am EDT / 3pm CEST** | Challenge launch **webinar** (Zoom; register to attend) |
| **Sep 15** | **First submission deadline** — retrospective phase |
| TBD | Top-10 invited to prospective phase |

---

## How to participate

1. **Create a free Synapse account** at <https://www.synapse.org> (Sage Bionetworks).
2. **Find the challenge project** — the announcement's *"Submit your predictions here"*
   link points to the Synapse project:
   `https://www.synapse.org/Synapse:syn75349604` (verify the synID is current).
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

---

## Sources

- DREAM x CACHE Target 2035 challenge announcement (SGC / MAINFRAME newsletter)
- [CACHE — Critical Assessment of Computational Hit-finding Experiments](https://cache-challenge.org/)
- [Target 2035 (overview)](https://en.wikipedia.org/wiki/Target_2035)
- [DREAM Challenges](https://en.wikipedia.org/wiki/DREAM_Challenges)
- [Sage Bionetworks](https://en.wikipedia.org/wiki/Sage_Bionetworks)
- Synapse challenge project: `https://www.synapse.org/Synapse:syn75349604`
  *(login required; could not be fetched here — verify details directly)*
