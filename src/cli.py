"""ResistAI CLI -- AMR drug discovery powered by NVIDIA NIM biology models.

Usage: python -m src.cli <command> [options]
       resistai <command> [options]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI helpers (no deps)
# ---------------------------------------------------------------------------
_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"

def bold(t: str) -> str:   return _c("1", t)
def dim(t: str) -> str:    return _c("2", t)
def red(t: str) -> str:    return _c("31", t)
def green(t: str) -> str:  return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)
def blue(t: str) -> str:   return _c("34", t)
def cyan(t: str) -> str:   return _c("36", t)
def mag(t: str) -> str:    return _c("35", t)

def badge(label: str, ok: bool) -> str:
    sym = green("ON") if ok else red("OFF")
    return f"[{label}: {sym}]"

def table(headers: list[str], rows: list[list[str]], widths: list[int] | None = None) -> str:
    """Render a simple ASCII table."""
    if not widths:
        widths = [max(len(h), *(len(str(r[i])) for r in rows)) + 2 for i, h in enumerate(headers)]
    sep = "+" + "+".join("-" * w for w in widths) + "+"
    def _row(vals: list[str]) -> str:
        cells = [str(v).ljust(w) for v, w in zip(vals, widths)]
        return "|" + "|".join(cells) + "|"
    lines = [sep, _row(headers), sep]
    for r in rows:
        lines.append(_row(r))
    lines.append(sep)
    return "\n".join(lines)

def progress(msg: str, pct: float) -> None:
    bar_w = 30
    filled = int(bar_w * pct)
    bar = green("=" * filled) + dim("-" * (bar_w - filled))
    sys.stderr.write(f"\r  [{bar}] {pct*100:5.1f}%  {msg[:60]:<60}")
    sys.stderr.flush()
    if pct >= 1.0:
        sys.stderr.write("\n")

# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------
def _load_env() -> None:
    """Load .env from project root into os.environ (simple key=value parser)."""
    for candidate in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]:
        if candidate.is_file():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip().strip("'\"")
                    os.environ.setdefault(k.strip(), v)
            break

# ---------------------------------------------------------------------------
# Lazy imports (keep startup fast)
# ---------------------------------------------------------------------------
def _nim():
    from src.models.nim_client import NIMClient
    return NIMClient()

def _orchestrator(cb=None):
    from src.pipeline.orchestrator import PipelineOrchestrator
    return PipelineOrchestrator(progress_callback=cb)

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    """Run the full AMR drug discovery pipeline."""
    _load_env()
    print(bold(cyan("\n  ResistAI  ")) + dim("AMR Drug Discovery Pipeline"))
    print(dim(f"  Pathogen: {args.pathogen}  |  Max drugs: {args.max_drugs}  |  Novel: {args.novel}\n"))

    def _cb(stage: str, pct: float, msg: str) -> None:
        if not args.json:
            progress(msg, pct)

    t0 = time.time()
    orch = _orchestrator(cb=_cb)
    try:
        results = orch.run_full_pipeline(
            pathogen_name=args.pathogen,
            max_drugs=args.max_drugs,
            generate_novel=args.novel,
        )
    except Exception as exc:
        print(red(f"\n  Error: {exc}"))
        return 1

    dur = time.time() - t0

    if args.json:
        print(json.dumps(results.to_dict(), indent=2))
        return 0

    # Pretty output
    meta = results.metadata
    models = meta.get("models_used", [])
    print(bold("\n  Models used: ") + "  ".join(badge(m.split("(")[0].strip(), True) for m in models))
    print()

    # Targets table
    print(bold("  Targets Discovered"))
    rows = [[t.name, t.pdb_code, f"{t.druggability_score:.3f}", t.function[:40]] for t in results.targets]
    print(table([" Name", " PDB", " Score", " Function"], rows, [18, 8, 9, 44]))

    # Top candidates table
    if results.top_candidates:
        print(bold("\n  Top Drug Candidates"))
        rows = []
        for c in results.top_candidates[:10]:
            rows.append([
                f" #{c.rank}", f" {c.drug_name}", f" {c.binding_affinity:.3f}",
                f" {c.safety_score:.3f}", f" {c.overall_score:.4f}", f" {c.regulatory_pathway}",
            ])
        print(table([" Rank", " Drug", " Binding", " Safety", " Overall", " Pathway"],
                     rows, [7, 24, 10, 9, 10, 14]))

    # Novel molecules
    novels = meta.get("novel_molecules", [])
    if novels:
        print(bold(f"\n  Novel Molecules Generated: {len(novels)}"))
        for n in novels[:5]:
            smi = n.get("smiles", "?")[:50]
            print(f"    {green('*')} QED={n.get('qed_score', 0):.3f}  seed={n.get('seed_drug', '?')}  {dim(smi)}")

    print(dim(f"\n  Completed in {dur:.1f}s  |  {meta.get('compounds_screened', 0)} compounds screened\n"))
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    """Predict protein-ligand binding via Boltz-2."""
    _load_env()
    nim = _nim()
    print(bold(cyan("  Boltz-2 Binding Prediction\n")) if not args.json else "", end="")
    t0 = time.time()
    result = nim.predict_binding(args.sequence, args.smiles)
    dur = time.time() - t0

    if args.json:
        print(json.dumps(asdict(result) | {"duration_s": round(dur, 2)}, indent=2, default=str))
        return 0 if result.success else 1

    if not result.success:
        print(red("  Prediction failed. Check API key and inputs."))
        return 1

    rows = [
        [" Confidence", f" {result.confidence_score:.4f}"],
        [" pTM", f" {result.ptm_score:.4f}"],
        [" ipTM", f" {result.iptm_score:.4f}"],
        [" Ligand ipTM", f" {result.ligand_iptm_score:.4f}"],
        [" Complex pLDDT", f" {result.complex_plddt:.4f}"],
        [" Complex ipLDDT", f" {result.complex_iplddt:.4f}"],
    ]
    print(table([" Metric", " Value"], rows, [18, 14]))
    print(dim(f"  {dur:.1f}s elapsed\n"))
    return 0


def cmd_fold(args: argparse.Namespace) -> int:
    """Fold a protein sequence via ESMFold."""
    _load_env()
    nim = _nim()
    print(bold(cyan("  ESMFold Protein Structure Prediction\n")) if not args.json else "", end="")
    t0 = time.time()
    result = nim.fold_protein(args.sequence)
    dur = time.time() - t0

    if args.json:
        d = asdict(result)
        d["pdb_string"] = d["pdb_string"][:200] + "..." if len(d["pdb_string"]) > 200 else d["pdb_string"]
        print(json.dumps(d | {"duration_s": round(dur, 2)}, indent=2, default=str))
        return 0 if result.success else 1

    if not result.success:
        print(red("  Folding failed. Check API key and sequence."))
        return 1

    if args.output:
        Path(args.output).write_text(result.pdb_string)
        print(green(f"  Wrote PDB to {args.output}"))
    else:
        print(dim(f"  PDB structure: {len(result.pdb_string)} chars (use --output to save)"))

    print(f"  Sequence length: {result.sequence_length}")
    print(dim(f"  {dur:.1f}s elapsed  |  {result.elapsed_ms:.0f}ms API time\n"))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate novel molecules via MolMIM."""
    _load_env()
    nim = _nim()
    print(bold(cyan("  MolMIM Molecule Generation\n")) if not args.json else "", end="")
    t0 = time.time()
    result = nim.generate_molecules(
        seed_smiles=args.seed,
        num_molecules=args.n,
        property_name=args.optimize,
        min_similarity=0.3,
    )
    dur = time.time() - t0

    if args.json:
        print(json.dumps(asdict(result) | {"duration_s": round(dur, 2)}, indent=2, default=str))
        return 0 if result.success else 1

    if not result.success:
        print(red("  Generation failed. Check API key and seed SMILES."))
        return 1

    print(f"  Generated {green(str(result.num_generated))} molecules  |  optimize: {args.optimize}")
    rows = []
    for i, mol in enumerate(result.molecules):
        smi = mol.get("sample", "?")
        score = mol.get("score", 0)
        rows.append([f" {i+1}", f" {score:.4f}", f" {smi[:52]}"])
    print(table([" #", f" {args.optimize}", " SMILES"], rows, [5, 10, 55]))
    print(dim(f"  {dur:.1f}s elapsed\n"))
    return 0


def cmd_dock(args: argparse.Namespace) -> int:
    """Dock a molecule into a protein via DiffDock."""
    _load_env()
    nim = _nim()
    print(bold(cyan("  DiffDock Molecular Docking\n")) if not args.json else "", end="")

    # Need a folded structure first
    if not args.json:
        print(dim("  Folding protein with ESMFold first..."))
    fold = nim.fold_protein(args.sequence)
    if not fold.success:
        print(red("  Could not fold protein. Cannot dock."))
        return 1

    t0 = time.time()
    result = nim.dock_molecule(fold.pdb_string, args.smiles, num_poses=args.poses)
    dur = time.time() - t0

    if args.json:
        d = asdict(result)
        d["ligand_positions"] = [p[:80] + "..." if len(p) > 80 else p for p in d["ligand_positions"]]
        print(json.dumps(d | {"duration_s": round(dur, 2)}, indent=2, default=str))
        return 0 if result.success else 1

    if not result.success:
        print(red("  Docking failed."))
        return 1

    print(f"  Generated {green(str(result.num_poses))} docking poses")
    rows = []
    for i, conf in enumerate(result.position_confidence):
        rows.append([f" {i+1}", f" {conf:.4f}"])
    print(table([" Pose", " Confidence"], rows, [8, 14]))
    print(dim(f"  {dur:.1f}s elapsed\n"))
    return 0


def cmd_design_binder(args: argparse.Namespace) -> int:
    """Design a protein binder via RFdiffusion + ProteinMPNN."""
    _load_env()
    nim = _nim()
    print(bold(cyan("  RFdiffusion + ProteinMPNN Binder Design\n")) if not args.json else "", end="")

    if not args.json:
        print(dim("  Folding target protein..."))
    fold = nim.fold_protein(args.sequence)
    if not fold.success:
        print(red("  Could not fold target protein."))
        return 1

    t0 = time.time()
    rf = nim.design_binder(fold.pdb_string, contigs=args.contigs)
    if not rf.success:
        print(red("  RFdiffusion design failed."))
        return 1 if not args.json else (print(json.dumps({"success": False})) or 1)

    mpnn = nim.design_sequence(rf.pdb_string)
    dur = time.time() - t0

    out = {
        "backbone_residues": rf.num_residues,
        "rfdiffusion_ms": rf.elapsed_ms,
        "sequences_designed": mpnn.num_sequences,
        "sequences": mpnn.sequences,
        "duration_s": round(dur, 2),
        "success": rf.success and mpnn.success,
    }

    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0 if out["success"] else 1

    print(f"  Backbone: {green(str(rf.num_residues))} residues  |  RFdiffusion: {rf.elapsed_ms:.0f}ms")
    if mpnn.success:
        print(f"  ProteinMPNN designed {green(str(mpnn.num_sequences))} sequences")
        for seq in mpnn.sequences[:3]:
            s = seq.get("sequence", "")[:60]
            sc = seq.get("score", 0)
            print(f"    score={sc:.4f}  {dim(s)}...")
    print(dim(f"  {dur:.1f}s elapsed\n"))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """Check which NIM endpoints are reachable."""
    _load_env()
    nim = _nim()
    if not nim.available:
        msg = "NVIDIA_API_KEY not set"
        if args.json:
            print(json.dumps({"error": msg, "endpoints": {}}))
        else:
            print(red(f"  {msg}. Set it in .env or environment.\n"))
        return 1

    print(bold(cyan("  NIM Endpoint Health Check\n")) if not args.json else "", end="")
    t0 = time.time()
    status = nim.health_check()
    dur = time.time() - t0

    if args.json:
        print(json.dumps({"endpoints": status, "duration_s": round(dur, 2)}))
        return 0

    rows = []
    for name, ok in status.items():
        sym = green("READY") if ok else red("DOWN ")
        rows.append([f" {name}", f" {sym}"])
    print(table([" Endpoint", " Status"], rows, [16, 10]))
    total = sum(status.values())
    print(dim(f"  {total}/{len(status)} endpoints ready  |  {dur:.1f}s\n"))
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    """List available NIM biology models."""
    _load_env()
    from src.models.nim_client import ENDPOINTS
    has_key = bool(os.environ.get("NVIDIA_API_KEY"))

    models_info = [
        ("ESMFold",      "esmfold",      "Protein structure prediction"),
        ("Evo2-40b",     "evo2",         "Genomic sequence generation"),
        ("Boltz-2",      "boltz2",       "Protein-ligand binding prediction"),
        ("MolMIM",       "molmim",       "Novel molecule generation"),
        ("RFdiffusion",  "rfdiffusion",  "De novo protein backbone design"),
        ("ProteinMPNN",  "proteinmpnn",  "Sequence design for backbones"),
        ("DiffDock",     "diffdock",     "Molecular docking (3D poses)"),
    ]

    if args.json:
        out = [{"name": n, "key": k, "url": ENDPOINTS[k], "description": d,
                "api_key_set": has_key} for n, k, d in models_info]
        print(json.dumps(out, indent=2))
        return 0

    print(bold(cyan("\n  NVIDIA NIM Biology Models")) + f"  {badge('API Key', has_key)}\n")
    rows = [[f" {n}", f" {k}", f" {d}"] for n, k, d in models_info]
    print(table([" Model", " Key", " Description"], rows, [16, 14, 42]))
    print()
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="resistai",
        description="ResistAI -- AMR drug discovery CLI powered by NVIDIA NIM",
    )
    p.add_argument("--json", action="store_true", help="Output as JSON")
    sub = p.add_subparsers(dest="command", help="Command to run")

    def _sub(name: str, **kw) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, **kw)
        sp.add_argument("--json", action="store_true", default=False, help="Output as JSON")
        return sp

    # run
    r = _sub("run", help="Run the full drug discovery pipeline")
    r.add_argument("--pathogen", default="acinetobacter_baumannii", help="Target pathogen")
    r.add_argument("--max-drugs", type=int, default=100, help="Max compounds to screen")
    r.add_argument("--novel", action="store_true", help="Enable novel molecule generation")

    # predict
    pr = _sub("predict", help="Predict protein-ligand binding (Boltz-2)")
    pr.add_argument("--sequence", required=True, help="Protein amino acid sequence")
    pr.add_argument("--smiles", required=True, help="Ligand SMILES string")

    # fold
    f = _sub("fold", help="Fold a protein sequence (ESMFold)")
    f.add_argument("--sequence", required=True, help="Amino acid sequence")
    f.add_argument("--output", default=None, help="Output PDB file path")

    # generate
    g = _sub("generate", help="Generate novel molecules (MolMIM)")
    g.add_argument("--seed", required=True, help="Seed SMILES string")
    g.add_argument("--n", type=int, default=5, help="Number of molecules")
    g.add_argument("--optimize", default="QED", help="Property to optimize")

    # dock
    d = _sub("dock", help="Dock molecule into protein (DiffDock)")
    d.add_argument("--sequence", required=True, help="Protein amino acid sequence")
    d.add_argument("--smiles", required=True, help="Ligand SMILES string")
    d.add_argument("--poses", type=int, default=5, help="Number of docking poses")

    # design-binder
    db = _sub("design-binder", help="Design protein binder (RFdiffusion + ProteinMPNN)")
    db.add_argument("--sequence", required=True, help="Target protein sequence")
    db.add_argument("--contigs", default="10-30/A1-60/10-30", help="Contig specification")

    # health / models
    _sub("health", help="Check NIM endpoint availability")
    _sub("models", help="List available NIM biology models")

    return p


_DISPATCH = {
    "run": cmd_run,
    "predict": cmd_predict,
    "fold": cmd_fold,
    "generate": cmd_generate,
    "dock": cmd_dock,
    "design-binder": cmd_design_binder,
    "health": cmd_health,
    "models": cmd_models,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # --json may appear before or after subcommand; ensure it's True if set anywhere
    raw = argv if argv is not None else sys.argv[1:]
    if "--json" in raw:
        args.json = True

    if not args.command:
        parser.print_help()
        return 1

    handler = _DISPATCH.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print(yellow("\n  Interrupted."))
        return 130
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}))
        else:
            print(red(f"\n  Error: {exc}\n"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
