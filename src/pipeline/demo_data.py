"""Pre-computed demo data used as fallback when NIM APIs are unavailable.

Contains a curated AMR drug library and demo target sequences. Keeps
hardcoded biological data out of the pipeline orchestration logic.
"""
from __future__ import annotations

DEMO_DRUG_LIBRARY: list[dict[str, str]] = [
    {"name": "Sulbactam-Durlobactam", "smiles": "CC1(C)C(C(=O)O)N2C(=O)CC2S1(=O)=O", "moa": "Beta-lactamase inhibitor combo", "phase": "Approved (2023)"},
    {"name": "Cefiderocol", "smiles": "CC1=C(C(=O)O)N2C(=O)[C@@H](NC(=O)/C(=N\\OC)c3csc(N)n3)[C@H]2SC1", "moa": "Siderophore cephalosporin", "phase": "Approved"},
    {"name": "Eravacycline", "smiles": "CN(C)[C@H]1[C@@H]2C[C@@H]3Cc4c(O)c(O)c(NC(=O)CN5CCCC5)c(O)c4C(=O)C3=C(O)[C@@]2(O)C(=O)C(C(N)=O)=C1O", "moa": "Tetracycline (ribosome)", "phase": "Approved"},
    {"name": "Plazomicin", "smiles": "NCC1OC(OC2C(N)CC(N)C(OC3OCC(O)C(O)C3N)C2O)C(O)C(O)C1O", "moa": "Aminoglycoside (ribosome)", "phase": "Approved"},
    {"name": "Meropenem-Vaborbactam", "smiles": "CC(O)C1C2CC(=O)N2C1C(=O)O", "moa": "Carbapenem + BLI", "phase": "Approved"},
    {"name": "Taniborbactam", "smiles": "OB(O)C1CCC(CC(=O)NC2CCNC2)CC1", "moa": "Bicyclic boronate BLI", "phase": "Phase 3"},
    {"name": "Zidebactam", "smiles": "O=C(O)C1N2C(=O)CC2S1(=O)=O", "moa": "DBO BLI + PBP2 binder", "phase": "Phase 3"},
    {"name": "Apramycin", "smiles": "NC1CC(N)C(OC2OC(CO)C(O)C(O)C2N)OC1OC1OCC(N)C(O)C1O", "moa": "Aminoglycoside (EGA)", "phase": "Phase 2"},
    {"name": "Zoliflodacin", "smiles": "CC1CC(=O)N(c2cc3c(cc2F)C(=O)C(=CN3C2CC2)C(=O)O)C1", "moa": "Spiropyrimidinetrione (GyrB)", "phase": "Phase 3"},
    {"name": "Gepotidacin", "smiles": "CC(C)n1cc2c(=O)c3cc(N4CCC(N)CC4)c(F)cc3n(C3CCC3)c2c1=O", "moa": "Triazaacenaphthylene (GyrA)", "phase": "Phase 3"},
    {"name": "Murepavadin", "smiles": "CC(C)CC(NC(=O)C(CC(=O)O)NC(=O)C(CO)NC=O)C(=O)O", "moa": "LptD inhibitor (outer membrane)", "phase": "Phase 1"},
    {"name": "SPR206", "smiles": "CC(=O)NC(CCCCN)C(=O)NC(CC(=O)O)C(=O)O", "moa": "Polymyxin derivative", "phase": "Phase 2"},
]


DEMO_SEQUENCES: dict[str, str] = {
    "NDM-1": "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETGDQRFGDLVFRQLAPNVWQHTSYLDMPGFGAVASNGLIVRDGGRVLVVDTAWTDDQTAQILNWIKQEINLPVALAVVTHAHQDKMGGMDALHAAGIATYANALSNQLAPQEGMVAAQHSLTFAANGWVEPATAPNFGPLKVFYPGPGHTSDNITVGIDGTDIAFGGCLIKDSKAKSLGNLGDADTEHYAASPCSSMAK",
    "OXA-23": "MMKKTLCALIAVSLTTAAGCCENQFNISTSNIHFAGDEVYAQFMDMVNEQGDGQWF",
    "PBP2a": "MKKISTLALLTFIVFGSSGLQEQNKITVNGISVAYAKVDNLKNATSTYEFSIAVGAMTENALKELKKVGDTIIKKEIASGSMTIDQLTAVVNRMDADFMKNEYDNLIRSYATGAQVAKFGFTDIVKQVNALNPENPLLSAEKIMLQLDKNAIFAKNLLNP",
    "DNA Gyrase": "MSDLAREITPVNIEEELKSSYLDYAMSVIVGRALPDVRDGLKPVHRRVLYAMNVLGNDWNKAYKKSARVVGDVIGKYHPHGDSAVYDTIVRMAQPFSLRYMLVDGQGNFGSIDGDSAAAMRYTEIRLAKIAHELMADLEKETVDFVDNYDGTEKIPDVMPTKIPNLLVNGSSGIAVGMATNIPPHNLTEVINGCLAYIDDEDISIEGLMEHIPGPDFPTAAIINGRRGIEEAYRTGRGKVYIRARAEVEVDAKTGRETIIVHEI",
    "KPC-2": "MSLYRRLVLLSCLSWPLAGFSATALTNLVAEPFAKLEQDFGGSIGVYAMDTGSGATVSYRAEERFPLCSSFKGFLAAAVLARSQQQAGLLDTPIRYGKNALVPWSPISEKYLTTGMTVAELSAAAVQYSDNAAANLLLKELGGPAGLTAFMRSIGDTTFRLDRWELELNSAIPGDARDTSSPRAVTESLQKIFLSETGAGKHVVPGAVLGEYRLYQSAGKLLPEQLPELQA",
    "PBP3": "MKKHSLTTLALFISATFAQADSQKNAGEKRFAPVAEKMKSTGKDVF",
    "LpxC": "MELPNIMHPVAKLSTALAAALMLSGCMPGEIRPTIGQQMETGDQRFGDLVF",
    "MexB": "MNIRNIFHKHDAKYTFYIISALSLLSLVAVTFRFVVSAQESMNIQFPGDLKQNEQRF",
    "LasR": "MAEYQNIFVDHINELKTMPSHRLSARYNKQGFAGLLTPEWLAQHGISMYVGEELRQH",
}
