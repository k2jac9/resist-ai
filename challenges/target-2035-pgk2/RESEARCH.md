# Deep Research Dossier — Second Target 2035 DEL-ML Challenge (PGK2)

> Companion to [`README.md`](./README.md) (the concise participation brief).
> This dossier goes deeper on the science, the data, the competitive landscape, and a
> concrete modeling strategy. **Compiled & fact-checked 2026-06-18** from public
> sources (see [Sources](#sources)). Claims are tagged **[verified]** (confirmed
> against a cited primary/official source), **[reported]** (stated by a credible
> secondary source), or **[inference]** (reasoned analysis, not a quoted fact).

---

## 1. Executive summary

- The **Second Target 2035 DEL-ML Challenge** — branded **"DREAM × CACHE Target 2035
  Drug Discovery Challenge"** (Synapse `syn75349604`) — is a **computational**
  hit-finding competition to predict small molecules that bind **phosphoglycerate
  kinase 2 (PGK2)**, selectively over its homologue **PGK1**. **[verified]**
- It is the **successor** to the *First* DREAM Target 2035 Drug Discovery Challenge
  (`syn65660836`, 2025) and is **distinct from CACHE Challenge #7**, a separate
  wet-lab CACHE challenge on the same target that ran **Aug 12 – Oct 10, 2025** and
  produced much of the experimental data. **[verified]**
- **Format:** train ML on a **~890M-compound DEL** screen, **retrospectively** retrieve
  the **~450 confirmed actives** hidden in a **400K ASMS** set (with an active-learning
  round), then a **prospective** phase where the top ~10 teams predict novel hits from
  **Enamine** that the organizers synthesize and assay. **[verified / reported]**
- **Why it's hard:** DEL data is noisy and indirectly labeled; there is a **train→test
  domain shift** (DEL → ASMS); and **PGK2/PGK1 selectivity** hinges on a **two-residue**
  difference in an otherwise near-identical active site. **[verified / inference]**
- **Timeline (2026):** launch webinar **Jul 7**, first (retrospective) submission
  **Sep 15**. **[verified]**

---

## 2. The Target 2035 initiative (context)

Target 2035 is the SGC-led open-science movement to **"develop a pharmacological
modulator for every protein in the human proteome by 2035."** **[verified]** Its thesis
is that the field's bottleneck — **hit-finding** — is still "experimental, expensive,
and unscalable," and must be turned into a **computational** discipline. **[verified]**

Mechanics that matter for this challenge:
- **Data at scale:** generate protein–ligand binding datasets for **2,000+ human
  proteins** using **AS-MS** and **DEL** screening, and release everything (including
  negative results) through the ML-ready **AIRCHECK** platform. **[verified]**
- **Open benchmarking:** run competitions (CACHE; the Target 2035 DREAM challenges) to
  measure and improve predictive models on prospective, experimentally-tested
  endpoints. **[verified]**
- **MAINFRAME:** an international network of ML researchers / computational chemists
  that provides curated datasets and experimental feedback, and supports equitable
  participation (incl. LMIC teams). **[verified / reported]**
- **Stated roadmap:** 2020–2025 "stealth mode" infrastructure build; 2025 onward
  executes the public vision; by **2030**, thousands of validated small-molecule hits
  + computational tools. **[verified]**

---

## 3. Challenge lineage — three things, one target

| # | Name | Type | When | Synapse / page | Relationship |
|---|------|------|------|----------------|--------------|
| 1 | **First DREAM Target 2035 Drug Discovery Challenge** | Computational DEL-ML | 2025 | `syn65660836` | The inaugural DEL-ML format this one iterates on. **[verified]** |
| 2 | **CACHE Challenge #7 — selective PGK2 inhibitors** | **Wet-lab** CACHE (design → make → assay) | **Aug 12 – Oct 10, 2025** | conscience.ca/event/cache7 | Same target; generated experimental data. Run by Conscience + SGC. **[verified]** |
| 3 | **Second Target 2035 DEL-ML Challenge ("DREAM × CACHE Target 2035")** | Computational DEL-ML | **2026** (Jul 7 launch, Sep 15 deadline) | `syn75349604` | **← this dossier.** **[verified]** |

**Why the distinction matters:** searching "CACHE #7 PGK2" surfaces the **2025 wet-lab**
challenge with an **Oct 10, 2025** deadline and a **~CA$100/compound**, no-quinazoline,
design-it-yourself format. That is **not** the challenge you'd enter computationally in
2026. Conflating them is the single easiest factual error to make here. **[inference]**

---

## 4. The target: PGK2 biology & druggability

**What it is.** Phosphoglycerate kinase 2 (PGK2) is a **testis-specific** glycolytic
enzyme that catalyzes the first ATP-generating step of glycolysis (1,3-bisphosphoglycerate
→ 3-phosphoglycerate). During spermatogenesis it **replaces** the ubiquitous somatic
isozyme **PGK1**. **[verified]**

**Why it's a contraceptive target.** Male mice lacking PGK2 show **markedly reduced
sperm motility and ATP**, i.e. impaired fertility — making PGK2 an attractive
**non-hormonal male contraceptive** target, a space actively pursued under the **Gates
Foundation non-hormonal contraceptive program**. **[verified / reported]**

**Druggability caveats (important for expectations):**
- **Partial redundancy:** `Pgk2−/−` males are subfertile but **sired occasional pups** —
  unlike `Gapdhs−/−` males — implying **compensatory pathways**. In particular,
  **acylphosphatase** (ACYP1/ACYP2, both detected in human sperm) can convert
  1,3-BPG → 3-PG, **bypassing** the PGK step. A real-world inhibitor may need to account
  for this escape route. **[verified]**
- **Tractability rating:** PGK2 is catalogued as **Tbio** on Pharos (biology
  well-studied, but not yet a clinically-precedented drug target). **[verified]**

**Structures available for modeling:**
- **Mouse PGK2:** apo and substrate-bound crystal structures — **2P9Q** (apo),
  **2P9T** (+3-phosphoglycerate), **2PAA** (+ATP + 3PG). **[verified]**
- **Human PGK1:** many PDB structures — the homology/selectivity reference. **[verified]**
- Caveat: PGK undergoes a large **open→closed hinge motion** on substrate binding
  (3PG induces a ~13° domain rotation), so **conformational state matters** for any
  docking/structure-based scoring. **[verified]**

---

## 5. The selectivity problem (PGK2 vs PGK1)

This is the scientific crux. The two isozymes' **active sites are highly similar**
(the literature describes PGK2's active site as "essentially identical" to PGK1, with
most divergence on a C-terminal face away from the active site). **[verified]** Yet the
challenge demands **orthosteric** selectivity. The handle, **confirmed on
cache-challenge.org**, is a **two-residue** pocket difference: **[verified]**

| Pocket position | PGK2 | PGK1 | Modeling implication |
|-----------------|------|------|----------------------|
| **242** | **Tyr (Y)** | **Phe (F)** | PGK2 gains a **polar -OH** — a potential H-bond donor/acceptor PGK1 lacks. **[inference]** |
| **255** | **Ala (A)** | **Thr (T)** | PGK2 is **smaller/less polar** here — a small **pocket/shape** difference vs PGK1's Thr. **[inference]** |

**Strategic reading [inference]:** selectivity likely comes from designing a ligand that
**engages the Tyr242 hydroxyl** (absent in PGK1) and/or **exploits the Ala255 cavity**
(occluded by PGK1's bulkier Thr). A competitive entry should score candidates on a
**ΔΔG / selectivity-margin** basis (PGK2 affinity *minus* PGK1 affinity), not raw PGK2
affinity — otherwise you'll surface potent-but-unselective glycolysis inhibitors.

> ⚠️ CACHE #7 additionally **excluded the quinazoline scaffold** (a known promiscuous
> chemotype). Whether that exclusion is inherited by the DEL-ML challenge is **not
> confirmed** — check the Synapse rules. **[reported / open question]**

---

## 6. The data, and why it's hard

### 6.1 DEL training set (~890M)
**DNA-encoded libraries** combinatorially assemble building blocks (synthons) onto DNA
barcodes, screen the whole pool against the target, and read out enrichment by
sequencing. The challenge releases **~890M SMILES with read counts + building-block
compositions**. **[verified]**

Difficulties **[verified / inference]**:
- **Indirect, noisy labels.** "Enrichment" (read count) ≠ affinity; it folds in PCR
  bias, matrix effects, truncated/side products, and DNA-tag artifacts.
- **Structured, not i.i.d.** Compounds share building blocks; naive random splits leak
  synthons between train/val and **overstate** performance. Use **building-block-disjoint
  splits**.
- **Massive class imbalance** and **count, not binary** signal — model the enrichment
  distribution, don't just threshold.

### 6.2 ASMS retrospective test set (400K → ~450 actives)
**Affinity-selection mass spectrometry** incubates a compound mixture with the protein,
separates bound from unbound, and identifies binders by MS. The test set is **400K
compounds containing ~450 confirmed true positives** to be **retrieved/ranked**.
**[verified]**

The hard part is the **DEL → ASMS domain shift [inference]**: you train on
DNA-tagged, enrichment-labeled DEL chemistry and must generalize to a **different
chemical population** assayed by a **different method**. Expect a real distribution gap;
validate with that shift in mind (e.g., scaffold/series-level holdouts).

### 6.3 Prospective source — Enamine
Phase 2 finalists predict **novel** binders from the **Enamine** in-stock catalog; the
organizers synthesize/procure and **experimentally test** them. **[verified / reported]**

---

## 7. Challenge mechanics

**Phase 1 — Retrospective (free, open).** Rank the 400K ASMS set to recover the hidden
~450 actives. Scoring rewards **diverse hit retrieval** — recovering **many distinct
chemical series**, not just many near-duplicates of one. An **active-learning** round is
part of this phase. **[verified / reported]**

**Phase 2 — Prospective (top ~10).** Predict **novel** Enamine hits; finalists procure
**~50 compounds (< ~$1,000 total)**; organizers fund **100%** of experimental testing.
Winners judged on (1) number of **novel chemical series** confirmed and (2) **overall
confirmed hits**. **[reported]**

**Costs / equity. [verified / reported]**
- Phase 1 free; Phase 2 small compound cost, testing covered.
- **Canadian** participants (via Conscience / Strategic Innovation Fund) eligible for up
  to **50%** cost reimbursement (≈ up to **$75K** SMEs / **$50K** academic, per phase).
- **MAINFRAME / LMIC** teams advancing to Phase 2 can have expenses covered by SGC.

**Key dates (2026). [verified]** Launch webinar **Jul 7**; retrospective submission
**Sep 15**; prospective invitations TBD. (Precedent: CACHE #7's deadline was extended to
**Oct 10, 2025** — extensions happen.)

---

## 8. A competitive modeling strategy (blueprint, not yet built)

> This is an **[inference]**-level plan for a serious entry — a separate engineering
> effort from this research brief.

1. **Splitting & validation.** Building-block-disjoint and scaffold-disjoint CV;
   simulate the DEL→ASMS shift with series-level holdouts. Never random-split DEL.
2. **DEL signal modeling.** Treat read counts as **count data** (e.g., negative-binomial
   / zero-inflated likelihoods) rather than binarizing; denoise against the matrix /
   no-target control where available.
3. **Featurization.** Combine **2D fingerprints** (ECFP/Morgan), **building-block /
   synthon** identity features, and a **message-passing GNN** on the molecular graph;
   consider pretrained chemical encoders.
4. **Selectivity head.** Predict **PGK2 binding and a PGK2−PGK1 margin**; rank by the
   margin so unselective glycolysis binders are demoted. Use the **242/255** pocket
   differences in any structure-based re-scoring.
5. **Structure-based re-scoring (optional).** Dock top candidates into **PGK2 (2P9Q/2PAA)
   vs PGK1**, in the appropriate **open/closed** state, and keep candidates that engage
   **Tyr242-OH** / the **Ala255** cavity.
6. **Diversity-aware ranking.** Because scoring rewards **diverse** retrieval,
   **cluster** candidates (e.g., Butina/Tanimoto) and submit **cluster representatives**
   to maximize recovered series — not a top-N list of near-duplicates.
7. **Active learning.** Budget for the AL round: pick **informative + diverse** queries
   (uncertainty × diversity), not just highest-scoring.

---

## 9. Free & frontier models you can use (NVIDIA + open)

> The challenge is computational and budget-light, so a **fully-free** model stack is
> realistic. Much of the NVIDIA half is **already wired into ResistAI** via NVIDIA NIM.
> **Practical constraint [inference]:** NIM free credits are limited (≈1k–5k calls), so
> use **self-hostable open weights** for the high-volume **890M-row DEL ranking**, and
> spend NIM credits only on **low-volume** structure/docking re-scoring and generation
> of your top candidates.

### 9.1 NVIDIA BioNeMo / NIM — free tier
**Access [reported]:** sign up to the **NVIDIA Developer Program** at **build.nvidia.com**,
open any model, *Get API Key* → an `nvapi-` key with **~1,000 inference credits**
(up to **5,000** on request) and a **~40 req/min** limit. Separately, BioNeMo models are
**fully open-source** (weights + code, `NVIDIA/bionemo-framework` and the
`NVIDIA-Digital-Bio` GitHub org) so you can **self-host for free**. **[verified]**

| NIM model | Relevance to the PGK2 challenge | In ResistAI? |
|-----------|----------------------------------|--------------|
| **Boltz-2** | Structure **+ binding-affinity** prediction → core **PGK2-vs-PGK1 selectivity** scoring | ✅ yes |
| **OpenFold3 / OpenFold2** | 3D structure prediction (build PGK2/PGK1 models where PDB gaps exist) | — (ESMFold ✅) |
| **DiffDock** | Blind **docking** of candidates into PGK2 vs PGK1 pockets | ✅ yes |
| **MolMIM** | Small-molecule **generative + latent embedding** (CMA-ES optimization) for Phase-2 novel hits | ✅ yes |
| **GenMol** | **Masked-diffusion, fragment-based** generation (SAFE) → scaffold-hop to **novel series** | — (add) |
| **ProteinMPNN / RFdiffusion** | Protein design (peripheral here) | ✅ yes |
| **Evo2-40B** | Genomic foundation model (not central to small-molecule binding) | ✅ yes |

All of the above are **verified** as present in the BioNeMo/NIM catalog. The upshot:
ResistAI's NVIDIA integration is **mostly plug-in** for the structure/generation half;
the main new add worth wiring is **GenMol** (fragment-based novel-series generation).

### 9.2 Open chemical/protein foundation models (free weights) — for DEL/ASMS ranking
These are the workhorses for the **890M DEL → 400K ASMS** ranking model (featurize, then
fine-tune a lightweight head). All have **open weights** you can self-host:

- **MoLFormer / MoLFormer-XL** (IBM) — transformer pretrained on **~1.1B SMILES**; strong
  molecular embeddings for property/binding ranking (`ibm/MoLFormer-XL-both-10pct`). **[verified]**
- **ChemBERTa-2 / ChemBERTa-3** (DeepChem) — open SMILES language models **and** a
  standardized training/benchmark framework (2025). **[verified]**
- **Uni-Mol2** (DeepModeling) — **3D** molecular representation FM, weights released from
  **84M → 1.1B** params. **[verified]**
- **ESM-2** (Meta, `facebook/esm2_t33_650M_UR50D`) — protein embeddings of the **PGK2 /
  PGK1 sequences** to build selectivity features. **[verified]** (ResistAI already uses ESM-2 650M.)

### 9.3 DEL-specific methods (open code / papers)
- **DEL-Ranking** (arXiv 2410.14946) — a **ranking-correction denoising** framework for
  DEL affinities; directly targets the noisy-label problem in step 2 of the blueprint. **[verified]**
- **"Enabling Open ML of DEL Selections"** (J. Med. Chem. 2025) — an **open DEL-ML
  framework + public DEL datasets** to prototype the pipeline before the real data drops. **[verified]**
- **"Widespread false negatives in DEL data: linker effects"** (Chem. Sci. 2025,
  `D5SC00844A`) — essential caveat: DEL labels have systematic **false negatives**. **[verified]**
- **AIRCHECK** — the **ML-ready platform** the challenge's DEL data is released through. **[verified]**

### 9.4 Free LLMs for agentic / reasoning glue (optional)
NVIDIA NIM also hosts **open frontier LLMs free** (e.g. **Llama-3.x**, **Nemotron**) for
agent orchestration / literature reasoning. ResistAI's **multi-provider `llm_client`**
(defaults to local **Ollama**) can point at these endpoints, so no paid LLM is required. **[reported / inference]**

### 9.5 A fully-free reference stack [inference]
1. **Featurize** SMILES with **MoLFormer / Uni-Mol2 + ECFP** (self-hosted, free).
2. **Train a denoising ranker** (DEL-Ranking-style) on the **890M DEL** — local/cluster GPU.
3. **Rank** the **400K ASMS** set; keep diverse top candidates.
4. **Selectivity re-score** the shortlist with **Boltz-2 + DiffDock** against **PGK2
   (2P9Q/2PAA) vs PGK1**, scoring engagement of **Tyr242-OH / the Ala255 cavity** — low
   call volume, fits NIM free credits.
5. **Cluster** (Butina/Tanimoto) and **submit diverse representatives**.
6. **Phase 2:** generate novel **Enamine-available** series with **MolMIM + GenMol**.

> Net: essentially **$0 in model costs** — open weights for the heavy DEL ranking, NIM
> free credits for the low-volume structure/generation steps.

---

## 10. How this maps onto ResistAI (reuse vs gaps)

ResistAI is an **antimicrobial-resistance** pipeline (NDM-1 / ESKAPE) — a **different
domain** — but parts transfer to a future real entry:

**Reusable [inference]:**
- `src/utils/chemistry.py` — RDKit fingerprints/descriptors → DEL/ASMS featurization.
- `src/pipeline/drug_screening/similarity_search.py` — **Tanimoto similarity + Butina
  clustering**, directly applicable to the **diverse-hit** ranking in step 6.
- `src/pipeline/drug_screening/molmim_generator.py` — generative chemistry for Phase 2
  novel-hit ideation.
- **Boltz-2 / DiffDock** clients — structure-based **PGK2-vs-PGK1** selectivity re-scoring.

**Gaps ResistAI does not cover [inference]:**
- **DEL-specific** data handling (synthon encodings, enrichment-count denoising,
  building-block-disjoint splits).
- A **large-scale ML classifier/ranker** trained on ~890M rows.
- **Domain-shift-aware** validation (DEL → ASMS).

> A real entry is the *"working baseline model"* scope — explicitly **out of scope** for
> this research brief, which only documents the challenge and how to participate.

---

## 11. Open questions to confirm on Synapse

- [ ] Does the **quinazoline exclusion** (from CACHE #7) apply to the DEL-ML challenge?
- [ ] Exact **submission format** (ID scheme, score/rank columns, # of predictions).
- [ ] Precise **scoring metric** for "diverse hit retrieval" (e.g., clustered recall).
- [ ] **Active-learning** round mechanics, budget, and timing.
- [ ] Any **deadline extension** beyond Sep 15, 2026.
- [ ] Data-use / licensing terms and whether DEL data is delivered via **AIRCHECK**.

---

## Sources

- [CACHE — Critical Assessment of Computational Hit-finding Experiments (full challenge list incl. PGK2 DEL-ML)](https://cache-challenge.org/critical-assessment-computational-hit-finding-experiments)
- [CACHE Challenge #7: selective PGK2 inhibitors — Conscience (Aug 12–Oct 10 2025; CA$100/compound; no-quinazoline)](https://conscience.ca/event/cache7/)
- ["Announcing the Second Target 2035 DEL-ML challenge" — M. Schapira (890M SMILES; 450 TPs/400K ASMS; Jul 7 / Sep 15)](https://www.linkedin.com/posts/matthieu-schapira-84312510_announcing-the-second-target-2035-del-ml-activity-7472639611945545731-aOeW)
- [Target 2035 — Structural Genomics Consortium (mission; AIRCHECK; MAINFRAME; roadmap)](https://www.thesgc.org/target2035)
- [Transforming Hit-Finding into a Computational Endeavor — SGC blog](https://www.thesgc.org/blogs/transforming-hit-finding-computational-endeavor-roadmap-open-science-drug-discovery)
- [First DREAM Target 2035 Drug Discovery Challenge — Synapse `syn65660836`](https://www.synapse.org/Synapse:syn65660836)
- [PGK2 essential for sperm function & male fertility (Danshina et al., Biol Reprod 2010) — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2802118/)
- [X-ray analysis of mouse PGK2 (open form; 13° closure on 3PG) — PubMed](https://pubmed.ncbi.nlm.nih.gov/18004764/)
- [Mouse PGK2 crystal structures — RCSB PDB: 2P9Q (apo)](https://www.rcsb.org/structure/2P9Q) · [2P9T (+3PG)](https://www.rcsb.org/structure/2P9T) · [2PAA (+ATP+3PG)](https://www.rcsb.org/structure/2PAA)
- [Pharos: PGK2 target page (Tbio classification)](https://pharos.nih.gov/targets/PGK2)

**Models & tooling (Section 9):**
- [NVIDIA NIM biology model catalog (Boltz-2, GenMol, DiffDock, MolMIM, OpenFold, Evo2…)](https://build.nvidia.com/explore/biology)
- [NVIDIA NIM for Boltz-2 — structure + binding-affinity docs](https://docs.nvidia.com/nim/bionemo/boltz2/latest/index.html)
- [NVIDIA NIM for GenMol — fragment-based generation (SAFE) docs](https://docs.nvidia.com/nim/bionemo/genmol/latest/overview.html)
- [BioNeMo Framework — open-source models & weights](https://github.com/NVIDIA/bionemo-framework)
- [NVIDIA NIM free API: credits & rate limits (secondary)](https://decodethefuture.org/en/nvidia-nim-api-explained/)
- [IBM MoLFormer-XL — open SMILES foundation model (Hugging Face)](https://huggingface.co/ibm/MoLFormer-XL-both-10pct)
- [ChemBERTa-3 — open chemical foundation model training framework (GitHub)](https://github.com/deepforestsci/chemberta3)
- [Uni-Mol — 3D molecular representation models (GitHub)](https://github.com/deepmodeling/Uni-Mol)
- [ESM-2 protein language model (Hugging Face)](https://huggingface.co/facebook/esm2_t33_650M_UR50D)
- [DEL-Ranking: ranking-correction denoising for DEL affinities (arXiv 2410.14946)](https://arxiv.org/pdf/2410.14946)
- [Enabling Open ML of DEL Selections (J. Med. Chem. 2025)](https://pubs.acs.org/doi/10.1021/acs.jmedchem.5c01972)
- [Widespread false negatives in DEL data: linker effects (Chem. Sci. 2025)](https://pubs.rsc.org/en/content/articlehtml/2025/sc/d5sc00844a)
- Synapse challenge project (login required): `https://www.synapse.org/Synapse:syn75349604`
