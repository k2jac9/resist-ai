"""Shared helpers, constants, and data for all UI tabs."""
from __future__ import annotations
import hashlib
import random
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------
_pmgr = None
_orch = None
_llm = None
_pmgr_loaded = False
_orch_loaded = False
_llm_loaded = False


def get_pmgr():
    global _pmgr, _pmgr_loaded
    if not _pmgr_loaded:
        _pmgr_loaded = True
        try:
            from src.data.pathogens import PathogenManager
            _pmgr = PathogenManager()
        except Exception:
            _pmgr = None
    return _pmgr


def get_orch():
    global _orch, _orch_loaded
    if not _orch_loaded:
        _orch_loaded = True
        try:
            from src.pipeline.orchestrator import PipelineOrchestrator
            _orch = PipelineOrchestrator()
        except Exception:
            _orch = None
    return _orch


def get_llm():
    global _llm, _llm_loaded
    if not _llm_loaded:
        _llm_loaded = True
        try:
            from src.models.llm_client import NebisLLM
            _llm = NebisLLM()
        except Exception:
            _llm = None
    return _llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _rr(lo: float, hi: float) -> float:
    return round(random.uniform(lo, hi), 2)


# ---------------------------------------------------------------------------
# Deterministic demo data (single source of truth across all tabs)
# ---------------------------------------------------------------------------
def get_demo_candidates(pathogen_key: str, n: int = 10) -> list[dict]:
    """Generate deterministic demo candidates for a pathogen.

    Uses fixed seed per (drug, pathogen) pair so scores are identical
    everywhere -- pipeline tab, compare tab, report tab.
    """
    rows = []
    for nm, sm, base_binding, expl, tech in _COMPOUNDS[:n]:
        # Stable hash: deterministic across processes regardless of PYTHONHASHSEED
        seed = int(hashlib.md5(f"{nm}:{pathogen_key}".encode()).hexdigest(), 16) % 10000
        drug_rng = random.Random(seed)
        aff = round(base_binding + drug_rng.uniform(-0.03, 0.03), 3)
        safety = round(drug_rng.uniform(0.60, 0.95), 3)
        overall = round(0.5 * aff + 0.3 * safety + 0.2 * drug_rng.uniform(0.7, 0.95), 3)
        rows.append({
            "Rank": 0,
            "drug_name": nm,
            "smiles": sm,
            "binding": aff,
            "safety": safety,
            "overall": overall,
            "why": expl,
            "tech": tech,
            "moa": expl,
            "phase": "Approved" if base_binding > 0.7 else "Phase 3",
        })
    rows.sort(key=lambda r: r["overall"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["Rank"] = i
    return rows


# Fixed druggability scores per target (no randomness)
_TARGET_DRUGGABILITY: dict[str, float] = {
    "NDM-1": 0.72,
    "OXA-23": 0.85,
    "PBP3": 0.91,
    "LpxC": 0.78,
    "PBP2a": 0.88,
    "DNA Gyrase": 0.93,
    "KPC-2": 0.82,
    "MexB": 0.69,
    "LasR": 0.74,
}


def get_demo_targets(pathogen_key: str) -> list[dict]:
    """Generate deterministic demo targets for a pathogen."""
    pmgr = get_pmgr()
    if pmgr and (info := pmgr.get_pathogen(pathogen_key)):
        rows = []
        for t in info.get("key_targets", []):
            name = t["name"]
            td = TARGET_DETAILS.get(name, {})
            drug_score = _TARGET_DRUGGABILITY.get(name, 0.75)
            rows.append({
                "\U0001f3af Target": name,
                "What It Does": td.get("plain", t.get("function", "")),
                "Druggability": f"{drug_score:.0%}",
                "Status": (
                    "No approved inhibitor" if "NDM" in name or "Van" in name
                    else "Approved drugs exist" if "PBP" in name
                    else "In development"
                ),
            })
        return rows
    return [{"\U0001f3af Target": "N/A", "What It Does": "Data unavailable",
             "Druggability": "\u2014", "Status": "\u2014"}]


def _demo_candidates_to_display(pathogen_key: str, n: int = 10) -> list[dict]:
    """Convert raw demo candidates to display format with percentage strings."""
    raw = get_demo_candidates(pathogen_key, n)
    rows = []
    for c in raw:
        rows.append({
            "Rank": str(c["Rank"]),
            "\U0001f48a Drug": c["drug_name"],
            "Binding": f"{c['binding']:.0%}",
            "Safety": f"{c['safety']:.0%}",
            "Overall": f"{c['overall']:.0%}",
            "Why It Works": c["why"],
        })
    return rows


def _to_df(data: list) -> Any:
    return pd.DataFrame(data) if pd else str(data)


def _mode_badge(demo: bool) -> str:
    """Return a visible badge indicating demo vs live mode."""
    if demo:
        return (
            "<div style='display:inline-block;padding:4px 12px;background:rgba(245,158,11,0.15);"
            "border:1px solid #F59E0B;border-radius:4px;color:#F59E0B;font-weight:600;"
            "font-size:0.85em;margin-bottom:8px'>"
            "⚡ MODE: DEMO — simulated data, no API calls</div>"
        )
    llm = get_llm()
    llm_ok = llm and llm.available
    try:
        from src.models.nim_client import NIMClient
        nim_ok = NIMClient().available
    except Exception:
        nim_ok = False
    models = []
    if nim_ok:
        models.append("NVIDIA NIM (7 models)")
    models.append("ESM-2 650M (local)")
    if llm_ok:
        models.append("Nebius AI (Qwen3-235B)")
    model_str = " + ".join(models) if models else "No API keys"
    return (
        "<div style='display:inline-block;padding:4px 12px;background:rgba(0,196,180,0.15);"
        "border:1px solid #00C4B4;border-radius:4px;color:#00C4B4;font-weight:600;"
        "font-size:0.85em;margin-bottom:8px'>"
        f"🟢 LIVE — {model_str}</div>"
    )


def _source_tag(source: str) -> str:
    """Return an inline tag indicating data source."""
    colors = {
        "demo": ("#F59E0B", "Simulated"),
        "llm": ("#00C4B4", "AI-Generated (Qwen3-235B)"),
        "heuristic": ("#94A3B8", "Heuristic Model"),
        "boltz2": ("#7C8CF8", "Boltz-2 (Nebius NIM)"),
        "esm2": ("#00C4B4", "ESM-2 (Meta FAIR)"),
    }
    color, label = colors.get(source, ("#999", source))
    return f"<span style='color:{color};font-size:0.8em;font-weight:600'>[ {label} ]</span>"


def _explain_score(score: float, context: str) -> str:
    if context == "affinity":
        if score > 0.8:
            return "Very strong fit — high likelihood of binding to the target"
        if score > 0.6:
            return "Good fit — promising candidate worth investigating"
        if score > 0.4:
            return "Moderate fit — may work but needs optimization"
        return "Weak fit — unlikely to be effective"
    if context == "safety":
        if score > 0.8:
            return "Excellent safety profile"
        if score > 0.6:
            return "Acceptable safety — manageable risk"
        if score > 0.4:
            return "Caution — notable safety concerns"
        return "Significant safety risks"
    if context == "overall":
        if score > 0.7:
            return "Strong candidate for further development"
        if score > 0.5:
            return "Worth investigating with additional studies"
        return "Low priority — better options available"
    return ""


# ---------------------------------------------------------------------------
# Constants & Data
# ---------------------------------------------------------------------------
PATHOGENS: dict[str, dict] = {
    "Acinetobacter baumannii": {
        "key": "acinetobacter_baumannii",
        "icon": "🦠", "who": "CRITICAL",
        "plain": "A deadly hospital-acquired infection resistant to nearly all antibiotics. WHO ranks it the #1 priority pathogen globally.",
        "analogy": "Think of it as a burglar that has learned to pick every lock we have.",
        "technical": "Gram-negative coccobacillus. Carbapenem-resistant via OXA-type and metallo-β-lactamases (NDM, VIM). Biofilm-forming. Key targets: LpxC (lipid A biosynthesis), BamA (outer membrane assembly), PBP3.",
    },
    "Staphylococcus aureus (MRSA)": {
        "key": "staphylococcus_aureus",
        "icon": "🔬", "who": "HIGH",
        "plain": "The 'superbug' behind dangerous skin, bloodstream, and surgical infections. Resistant to methicillin and related antibiotics.",
        "analogy": "Imagine a warrior wearing armor that deflects our best weapons.",
        "technical": "Gram-positive. mecA gene encodes PBP2a with low β-lactam affinity. Additional resistance via efflux (NorA), target modification (erm genes), and biofilm. Key targets: PBP2a, FtsZ, DNA gyrase.",
    },
    "Klebsiella pneumoniae": {
        "key": "klebsiella_pneumoniae",
        "icon": "⚠️", "who": "CRITICAL",
        "plain": "Causes pneumonia, bloodstream infections, and meningitis — especially in ICU patients. Carbapenem-resistant strains are a critical threat.",
        "analogy": "Like an invader that has built walls our strongest missiles can't penetrate.",
        "technical": "Gram-negative Enterobacterales. KPC-2/3 (Class A) and NDM-1 (Class B) carbapenemases. OmpK35/K36 porin loss reduces drug entry. Key targets: KPC-2 (PDB: 5UL8), NDM-1 (PDB: 3SPU), CTX-M-15.",
    },
    "Pseudomonas aeruginosa": {
        "key": "pseudomonas_aeruginosa",
        "icon": "🧫", "who": "CRITICAL",
        "plain": "Thrives in hospital environments — ventilators, catheters, wounds. Has built-in pumps that actively eject antibiotics.",
        "analogy": "Picture a fortress with pumps that flush out any poison we throw in.",
        "technical": "Gram-negative. Intrinsic resistance via MexAB-OprM efflux, AmpC β-lactamase, low outer membrane permeability. Acquires VIM/IMP metallo-β-lactamases. Key targets: MexB (PDB: 3W9I), LasR (PDB: 2UV0), PBP3.",
    },
}

_COMPOUNDS = [
    ("Sulbactam-Durlobactam", "O=C(O)[C@@H]1[C@@H](CC)S(=O)(=O)C1C", 0.91,
     "Blocks the enzyme that destroys antibiotics, restoring their effectiveness",
     "DBO β-lactamase inhibitor targeting PBP2 + Class D OXA enzymes. FDA approved 2023 (Xacduro). First CRAB-specific agent."),
    ("Cefiderocol", "CC(C)(ON=C(C(=O)O)c1nsc(N)n1)C(=O)NC1C=C(Cl)CS1", 0.87,
     "Disguises itself as iron to sneak past the bacteria's defenses — a 'Trojan Horse' antibiotic",
     "Siderophore cephalosporin exploiting bacterial iron uptake (TonB-dependent). Stable to all 4 Ambler classes of β-lactamases. FDA approved 2019 (Fetroja)."),
    ("Eravacycline", "CC(O)C1C(=O)N1C1C(C(O)=O)=C(SCCC)C1", 0.82,
     "A next-generation tetracycline designed to evade resistance pumps",
     "Fluorocycline. Evades tet(A), tet(B), tet(K), tet(M) resistance mechanisms. Active against CRAB and CRE. FDA approved 2018 (Xerava)."),
    ("Meropenem", "O=C(O)[C@@H]1/C(=C\\SC2CC(SC)C(C(=O)O)N2C1=O)C", 0.76,
     "A powerful 'last-resort' antibiotic — but resistance is growing",
     "Group 2 carbapenem. Broad-spectrum β-lactam targeting PBPs 1-4. Hydrolyzed by KPC, NDM, OXA-48. Used as benchmark comparator."),
    ("Plazomicin", "OB(O)C1CCC(CNC(=O)c2ccncc2)CC1", 0.73,
     "Engineered to dodge the enzymes that bacteria use to neutralize aminoglycosides",
     "Next-gen aminoglycoside resistant to AAC(6'), ANT(2''), APH(3') aminoglycoside-modifying enzymes. FDA approved 2018 (Zemdri)."),
    ("Taniborbactam", "O=C(O)[C@@H]1N2C(=O)C(NC(=O)N3CCCC3)=C2CS1(=O)=O", 0.69,
     "The first approved inhibitor of metallo-beta-lactamases — a brand new weapon",
     "Cyclic boronate β-lactamase inhibitor. First approved MBL inhibitor component. Active against NDM, VIM, KPC, OXA-48. FDA approved 2024 with cefepime."),
    ("Colistin", "CC(C)CC(NC(=O)C(CC(N)=O)NC(=O)C(CC(C)C)NC=O)C(=O)O", 0.64,
     "An old antibiotic brought back as a 'last line of defense' — toxic but effective",
     "Polymyxin E. Disrupts Gram-negative outer membrane via electrostatic LPS binding. Nephrotoxic (20-60%). Resistance via mcr-1 (lipid A modification). Last-resort only."),
    ("Gepotidacin", "CC1CC(=O)N(C1)c1ccc(F)c(F)c1", 0.61,
     "Attacks bacterial DNA replication through a completely new mechanism",
     "First-in-class triazaacenaphthylene. Novel dual-target: GyrA (different binding site from fluoroquinolones) + ParC. No cross-resistance with existing quinolones."),
    ("Aztreonam", "C(=C1/C(N2C1CC2)C(=O)O)\\SCCNC=N", 0.55,
     "Unique monobactam antibiotic that resists breakdown by metallo-enzymes",
     "Monobactam targeting PBP3. Intrinsically stable to metallo-β-lactamases (Class B). Synergistic with avibactam (covers serine β-lactamases). FDA approved for combination 2024-2025."),
    ("Apramycin", "C(=C/SC1CNC(S(N)(=O)=O)C1)\\C1N2C(C(O)=O)=C1OC2=O", 0.48,
     "Originally used in veterinary medicine — being repurposed for human superbugs",
     "4-monosubstituted 2-deoxystreptamine aminoglycoside. Unique ribosomal binding mode evades all known AMEs and 16S rRNA methyltransferases. Phase 1 clinical trial ongoing."),
]

TARGET_DETAILS = {
    "NDM-1": {"pdb": "3SPU", "uniprot": "C7C422", "class": "Metallo-β-lactamase (Ambler Class B)",
              "plain": "The bacteria's 'shield' — an enzyme that destroys our strongest antibiotics",
              "mechanism": "Zn²⁺-dependent hydrolysis of β-lactam ring. Requires 2 zinc ions in active site. No approved standalone inhibitor."},
    "OXA-23": {"pdb": "4JF4", "uniprot": "Q2L4R8", "class": "Serine β-lactamase (Ambler Class D)",
               "plain": "Another antibiotic-destroying enzyme, specific to A. baumannii",
               "mechanism": "Serine-based hydrolysis. Carbapenemase activity via unique omega loop conformation. Inhibited by durlobactam."},
    "PBP3": {"pdb": "6V1M", "uniprot": "A0A0D5YPF0", "class": "Penicillin-binding protein",
             "plain": "Part of the machinery that builds the bacteria's cell wall — a classic drug target",
             "mechanism": "Transpeptidase essential for peptidoglycan cross-linking during cell division. Target of cephalosporins and carbapenems."},
    "LpxC": {"pdb": "3UHM", "uniprot": "A3M7A1", "class": "UDP-3-O-acyl-N-acetylglucosamine deacetylase",
             "plain": "Makes a critical component of the bacteria's outer armor",
             "mechanism": "Catalyzes first committed step of lipid A biosynthesis. Zn²⁺-metalloenzyme. Essential in Gram-negatives. Multiple inhibitors in preclinical development."},
    "PBP2a": {"pdb": "1VQQ", "uniprot": "P07944", "class": "Altered penicillin-binding protein",
              "plain": "An altered protein that ignores methicillin-class antibiotics",
              "mechanism": "mecA-encoded transpeptidase with narrow active site cleft excluding most β-lactams. Allosteric triggering required for activity."},
    "DNA Gyrase": {"pdb": "2XCS", "uniprot": "P0A0K8", "class": "Type II topoisomerase (GyrA/GyrB)",
                   "plain": "Helps the bacteria copy its DNA — blocking it stops reproduction",
                   "mechanism": "Introduces negative supercoils into DNA. GyrA subunit is target of fluoroquinolones (QRDR mutations confer resistance)."},
    "KPC-2": {"pdb": "5UL8", "uniprot": "Q6PT52", "class": "Serine carbapenemase (Ambler Class A)",
              "plain": "An enzyme that chews up carbapenem antibiotics — our 'last resort' drugs",
              "mechanism": "Plasmid-encoded serine β-lactamase. Hydrolyzes all β-lactams. Inhibited by avibactam, vaborbactam."},
    "MexB": {"pdb": "3W9I", "uniprot": "P52477", "class": "RND efflux transporter",
             "plain": "A molecular pump that actively ejects antibiotics out of the cell",
             "mechanism": "Inner membrane component of MexAB-OprM tripartite efflux system. Exports fluoroquinolones, β-lactams, chloramphenicol. Powered by proton motive force."},
    "LasR": {"pdb": "2UV0", "uniprot": "P25084", "class": "Quorum sensing transcriptional regulator",
             "plain": "Controls the bacteria's ability to communicate and coordinate attacks",
             "mechanism": "LuxR-type receptor activated by 3-oxo-C12-HSL. Regulates virulence factors, biofilm formation, and elastase production."},
}

_EXAMPLE_TARGETS = {
    "NDM-1 (destroys carbapenems — no approved inhibitor)": {
        "sequence": "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETGDQRFGDLVFRQLAPNVWQHTSYLDMPGFGAVASNGLIVRDGGRVLVVDTAWTDDQTAQILNWIKQEINLPVALAVVTHAHQDKMGGMDALHAAGIATYANALSNQLAPQEGMVAAQHSLTFAANGWVEPATAPNFGPLKVFYPGPGHTSDNITVGIDGTDIAFGGCLIKDSKAKSLGNLGDADTEHYAASPCSSMAK",
        "smiles": "O=C(O)[C@@H]1N2C(=O)C(NC(=O)N3CCCC3)=C2CS1(=O)=O",
        "drug": "Taniborbactam",
    },
    "PBP2a / MRSA (methicillin resistance)": {
        "sequence": "MKKISTLALLTFIVFGSSGLQEQNKITVNGISVAYAKVDNLKNATSTYEFSIAVGAMTENALKELKKVGDTIIKKEIASGSMTIDQLTAVVNRMDADFMKNEYDNLIRSYATGAQVAKFGFTDIVKQVNALNPENPLLSAEKIMLQLDKNAIFAKNLLNP",
        "smiles": "CC(C)(ON=C(C(=O)O)c1nsc(N)n1)C(=O)NC1C=C(Cl)CS1",
        "drug": "Cefiderocol",
    },
    "DNA Gyrase (fluoroquinolone target)": {
        "sequence": "MSDLAREITPVNIEEELKSSYLDYAMSVIVGRALPDVRDGLKPVHRRVLYAMNVLGNDWNKAYKKSARVVGDVIGKYHPHGDSAVYDTIVRMAQPFSLRYMLVDGQGNFGSIDGDSAAAMRYTEIRLAKIAHELMADLEKETVDFVDNYDGTEKIPDVMPTKIPNLLVNGSSGIAVGMATNIPPHNLTEVINGCLAYIDDEDISIEGLMEHIPGPDFPTAAIINGRRGIEEAYRTGRGKVYIRARAEVEVDAKTGRETIIVHEI",
        "smiles": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
        "drug": "Ciprofloxacin",
    },
    "KPC-2 (carbapenem-destroying enzyme)": {
        "sequence": "MSLYRRLVLLSCLSWPLAGFSATALTNLVAEPFAKLEQDFGGSIGVYAMDTGSGATVSYRAEERFPLCSSFKGFLAAAVLARSQQQAGLLDTPIRYGKNALVPWSPISEKYLTTGMTVAELSAAAVQYSDNAAANLLLKELGGPAGLTAFMRSIGDTTFRLDRWELELNSAIPGDARDTSSPRAVTESLQKIFLSETGAGKHVVPGAVLGEYRLYQSAGKLLPEQLPELQA",
        "smiles": "OB(O)C(CC1CCCCC1)NC(=O)c1cccc(c1)C(=O)O",
        "drug": "Vaborbactam",
    },
}

_EXAMPLE_DRUGS_SAFETY = {
    "Ciprofloxacin (common antibiotic)": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
    "Meropenem (last-resort carbapenem)": "C(=C1/C(N2C(C2C)C(=O)O)SC1C)/C(=O)O",
    "Colistin (toxic but effective last line)": "CCC(C)CCCC(=O)NC(CC(N)=O)C(=O)NC(CC1=CNC2=CC=CC=C21)C(=O)NC(CC(C)C)C(=O)O",
    "Linezolid (MRSA antibiotic)": "O=C1ON(/C(=O)C1)c1ccc(N2CCOCC2)c(F)c1",
    "Amoxicillin (common penicillin)": "CC1(C)SC2C(NC(=O)C(N)c3ccc(O)cc3)C(=O)N2C1C(O)=O",
}

_CSS = """
.gradio-container{background:linear-gradient(135deg,#0A0F1E,#0F1829,#0A0F1E)!important;color:#E2E8F0!important}
.gr-button-primary{background:linear-gradient(90deg,#00C4B4,#009E91)!important;border:none!important;font-size:1.05em!important;font-weight:600!important}
.gr-button-primary:hover{background:linear-gradient(90deg,#00E0CE,#00C4B4)!important;transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,196,180,0.3)!important}
footer{display:none!important}
.built-with{display:none!important}
.recording-indicator{display:none!important}
h1{color:#00C4B4!important}
h2,h3{color:#00C4B4!important}
.evolved-banner{text-align:center;padding:18px 16px;background:linear-gradient(135deg,rgba(0,196,180,0.08),rgba(0,196,180,0.04));
border-radius:12px;margin-bottom:16px;border:1px solid rgba(0,196,180,0.25)}
.tab-nav button{color:#94A3B8!important;font-size:0.95em!important;transition:color 0.2s}
.tab-nav button:hover{color:#00C4B4!important;opacity:0.8}
.tab-nav button.selected{color:#00C4B4!important;border-color:#00C4B4!important}
blockquote{border-left:3px solid #00C4B4!important;padding-left:12px;opacity:0.9}
table{font-size:0.92em!important}
details{margin:8px 0;padding:8px 12px;background:rgba(0,196,180,0.05);border-radius:6px;border:1px solid rgba(0,196,180,0.15)}
details summary{font-weight:600}
code{background:rgba(0,196,180,0.1)!important;border:1px solid rgba(0,196,180,0.2)!important;border-radius:3px!important}
"""
