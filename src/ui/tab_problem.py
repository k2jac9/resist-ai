"""Tab: The Problem — AMR crisis overview and pathogen cards."""
from __future__ import annotations

from src.ui.common import PATHOGENS

_PROBLEM_MD = """
## The Crisis: Antibiotics Are Failing

<div style="display:flex;gap:20px;flex-wrap:wrap;margin:16px 0">
<div style="flex:1;min-width:200px;background:rgba(244,63,94,0.1);padding:20px;border-radius:8px;border-left:4px solid #F43F5E">
<div style="font-size:2.2em;font-weight:800;color:#F43F5E;margin-bottom:4px">1.27 million</div>
<div style="font-size:0.95em;opacity:0.85">Deaths per year from drug-resistant infections — more than HIV/AIDS or malaria</div>
</div>
<div style="flex:1;min-width:200px;background:rgba(245,158,11,0.1);padding:20px;border-radius:8px;border-left:4px solid #F59E0B">
<div style="font-size:2.2em;font-weight:800;color:#F59E0B;margin-bottom:4px">90%</div>
<div style="font-size:0.95em;opacity:0.85">Failure rate for new antibiotics in clinical trials</div>
</div>
<div style="flex:1;min-width:200px;background:rgba(124,140,248,0.1);padding:20px;border-radius:8px;border-left:4px solid #7C8CF8">
<div style="font-size:2.2em;font-weight:800;color:#7C8CF8;margin-bottom:4px">95%</div>
<div style="font-size:0.95em;opacity:0.85">Of large pharma companies have exited antibiotic R&D</div>
</div>
</div>

## Our Solution: AI Drug Repurposing

Instead of inventing new drugs from scratch (10-15 years, $2.6B), we use AI to find **existing approved drugs** that could work against resistant bacteria.

> **Analogy:** It's like discovering that a key you already own opens a lock you didn't know about.

### The Three-Step Pipeline

| Step | For Everyone | For Scientists |
|------|-------------|----------------|
| 🔍 **Discover** | Find the bacteria's weak spots | Evo2 (40B-param genomic model) + ESM-2 protein embeddings identify druggable targets |
| 💊 **Screen** | Test existing drugs against those weak spots | Boltz-2 predicts protein-ligand binding affinity (1000x faster than FEP) |
| 🛡️ **Verify** | Check each drug is safe for humans | ADMET prediction + off-target screening across 20 critical human proteins |

**~2,700 FDA-approved drugs** have never been systematically screened against resistant pathogens. AI can do it in minutes.
"""


def _pathogen_cards() -> str:
    lines = [
        "## ESKAPE Pathogens: The WHO's Most Dangerous\n",
        "> The name **ESKAPE** reflects these bacteria's ability to *escape* antibiotics. "
        "We focus on the 4 most critical pathogens with the highest resistance burden.\n",
    ]
    for label, info in PATHOGENS.items():
        col = "#F43F5E" if info["who"] == "CRITICAL" else "#FB923C"
        badge_bg = "rgba(244,63,94,0.15)" if info["who"] == "CRITICAL" else "rgba(251,146,60,0.15)"
        lines += [
            f"### {info['icon']} {label}",
            f"**WHO Priority:** <span style='display:inline-block;padding:1px 8px;background:{badge_bg};"
            f"border:1px solid {col};border-radius:10px;color:{col};font-weight:700;"
            f"font-size:0.85em'>{info['who']}</span>\n",
            f"{info['plain']}\n",
            f"*{info['analogy']}*\n",
        ]
        lines.append(
            f"<details><summary style='color:#00C4B4;cursor:pointer'>🔬 Technical Details</summary>"
            f"\n\n{info['technical']}\n\n</details>\n\n---\n"
        )
    return "\n".join(lines)
