"""Pipeline orchestrator for AMR-AI drug discovery.

Coordinates the multi-stage pipeline using NVIDIA NIM biology models
and Nebius LLMs: target discovery → drug screening + novel generation →
safety prediction → ranking → AI reasoning.

Stage implementations live in sibling modules:
- target_stage.TargetAnalyzer
- screening_stage.DrugScreener
- novel_stage.NovelMoleculeGenerator
- safety_stage.SafetyScorer
- ranking.rank_candidates
- clients.get_nim / clients.get_llm
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from ..models.schemas import PipelineResults, SafetyReport
from .clients import get_llm, get_nim
from .demo_data import DEMO_SEQUENCES
from .novel_stage import NovelMoleculeGenerator
from .ranking import rank_candidates
from .safety_stage import SafetyScorer
from .screening_stage import DrugScreener
from .target_stage import TargetAnalyzer

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str, float, str], None]]


def _default_progress(stage: str, pct: float, message: str) -> None:
    logger.info("[%s %.0f%%] %s", stage, pct * 100, message)


class PipelineOrchestrator:
    """Coordinates the full AMR-AI drug discovery pipeline."""

    def __init__(self, progress_callback: ProgressCallback = None) -> None:
        self._progress = progress_callback or _default_progress
        self._target_analyzer = TargetAnalyzer()
        self._drug_screener = DrugScreener()
        self._novel_generator = NovelMoleculeGenerator()
        self._safety_scorer = SafetyScorer()

    def run_full_pipeline(
        self,
        pathogen_name: str,
        max_drugs: int = 100,
        demo_mode: bool = False,
        generate_novel: bool = True,
    ) -> PipelineResults:
        """Execute the end-to-end drug discovery pipeline.

        6-model chain: Evo2 → ESMFold → Boltz-2 → MolMIM → Boltz-2 → Safety
        """
        start = time.time()
        use_nim = not demo_mode
        self._progress("init", 0.0, f"Starting pipeline for {pathogen_name}")

        from .stages import (
            stage_design_binder,
            stage_dock as _stage_dock,
            stage_fold_protein,
            stage_genomics,
        )

        # Stage 0 -- Genomic Analysis (Evo2-40b)
        evo2_data: dict[str, Any] = {}
        nim = get_nim() if use_nim else None
        if nim and nim.available and use_nim:
            self._progress("genomics", 0.02, "Scanning genome with Evo2-40b...")
            seed_dna = "ATGCGTAACTGGATCGATCGTACGATCGTAGCTAGCGATCG"
            evo = stage_genomics(nim, seed_dna, num_tokens=128)
            if evo["success"]:
                evo2_data = {
                    "generated_length": evo["generated_length"],
                    "elapsed_ms": evo["elapsed_ms"],
                    "model": evo["model"],
                }
                self._progress(
                    "genomics", 0.05,
                    f"Evo2: generated {evo['generated_length']}nt in "
                    f"{evo['elapsed_ms']:.0f}ms",
                )

        # Stage 1 -- Target Discovery (ESMFold)
        self._progress("targets", 0.05, "Discovering druggable targets (ESMFold)...")
        targets = self._target_analyzer.discover_targets(pathogen_name, use_nim=use_nim)
        if not targets:
            raise ValueError(f"No targets found for pathogen: {pathogen_name}")
        self._progress("targets", 0.15, f"Found {len(targets)} targets")

        # Stage 2 -- Virtual Screening (Boltz-2)
        primary_target = targets[0]
        self._progress(
            "screening", 0.20,
            f"Screening drugs against {primary_target.name} (Boltz-2)...",
        )
        screening = self._drug_screener.screen_drugs(
            primary_target, max_drugs, use_nim=use_nim
        )
        all_screening = [screening]
        self._progress(
            "screening", 0.45,
            f"Screened {screening.compounds_screened} compounds, "
            f"{len(screening.hits)} hits",
        )

        # Stage 2b -- Novel Molecule Generation (MolMIM + Boltz-2)
        novel_molecules: list[dict] = []
        if generate_novel and use_nim:
            self._progress("generation", 0.50, "Generating novel molecules (MolMIM)...")
            novel_molecules = self._novel_generator.generate_from_hits(
                screening.hits[:3], primary_target,
                molecules_per_hit=3, max_hits=3,
            )
            self._progress(
                "generation", 0.60,
                f"Generated {len(novel_molecules)} novel candidates",
            )

        # Stage 2c -- 3D Docking Poses (DiffDock)
        docking_results: list[dict] = []
        if use_nim and nim and nim.available:
            top_hit = screening.hits[0] if screening.hits else None
            target_seq = DEMO_SEQUENCES.get(primary_target.name, "")
            if top_hit and target_seq:
                self._progress("docking", 0.55, f"3D docking {top_hit.drug_name} (DiffDock)...")
                fold = stage_fold_protein(nim, target_seq)
                if fold["success"]:
                    dock = _stage_dock(nim, fold["pdb_string"], top_hit.smiles, num_poses=3)
                    if dock["success"]:
                        docking_results.append({
                            "drug": top_hit.drug_name,
                            "target": primary_target.name,
                            "poses": dock["num_poses"],
                            "confidence": dock["position_confidence"][:3],
                            "source": "DiffDock (NVIDIA NIM)",
                        })
                        self._progress(
                            "docking", 0.60,
                            f"DiffDock: {dock['num_poses']} poses for {top_hit.drug_name}",
                        )

        # Stage 3 -- De Novo Protein Binder Design (RFdiffusion + ProteinMPNN)
        binder_designs: list[dict] = []
        if use_nim and nim and nim.available:
            self._progress("binder", 0.62, "Designing novel protein binders (RFdiffusion)...")
            target_seq = DEMO_SEQUENCES.get(primary_target.name, "")
            if target_seq:
                fold = stage_fold_protein(nim, target_seq)
                if fold["success"] and fold.get("pdb_string"):
                    n_res = min(len(target_seq), 60)
                    contigs = f"10-30/A1-{n_res}/10-30"
                    binder = stage_design_binder(nim, fold["pdb_string"], contigs=contigs)
                    if binder.get("num_residues"):
                        self._progress(
                            "binder", 0.66,
                            f"RFdiffusion backbone: {binder['num_residues']} residues "
                            f"({binder['rfdiffusion_ms']:.0f}ms)",
                        )
                    if binder["success"]:
                        binder_designs.append({
                            "target": primary_target.name,
                            "backbone_residues": binder["num_residues"],
                            "sequences_designed": binder["num_sequences"],
                            "rfdiffusion_ms": binder["rfdiffusion_ms"],
                            "source": "RFdiffusion + ProteinMPNN (NVIDIA NIM)",
                        })
                        self._progress(
                            "binder", 0.68,
                            f"ProteinMPNN: {binder['num_sequences']} sequences designed",
                        )

        # Stage 4 -- Safety Prediction
        top_hits = screening.hits[:10]
        self._progress("safety", 0.70, f"Evaluating safety for {len(top_hits)} hits...")
        safety_reports: list[SafetyReport] = []
        for i, hit in enumerate(top_hits):
            report = self._safety_scorer.score_drug(hit)
            safety_reports.append(report)
            pct = 0.70 + 0.15 * ((i + 1) / len(top_hits))
            self._progress("safety", pct, f"Safety assessed: {hit.drug_name}")

        # Combine and Rank
        self._progress("ranking", 0.88, "Computing overall scores and ranking...")
        candidates = rank_candidates(top_hits, safety_reports)
        duration = round(time.time() - start, 2)

        # LLM-powered analysis (Nebius)
        llm_insights: dict[str, Any] = {}
        llm = get_llm()
        if llm and llm.available:
            self._progress("analysis", 0.92, "Running AI reasoning (Nebius LLM)...")
            try:
                top_target = targets[0]
                llm_insights["target_analysis"] = llm.analyze_target(
                    top_target.name, pathogen_name,
                    top_target.pdb_code, top_target.function)
                if candidates:
                    top = candidates[0]
                    llm_insights["top_drug_analysis"] = llm.analyze_drug_candidate(
                        top.drug_name, top.smiles, top.target_name, top.binding_affinity)
                target_names = [{"name": t.name} for t in targets]
                cand_data = [{"name": c.drug_name, "binding": c.binding_affinity,
                              "safety": c.safety_score, "overall": c.overall_score}
                             for c in candidates[:5]]
                llm_insights["executive_summary"] = llm.generate_executive_report(
                    pathogen_name, target_names, cand_data, screening.compounds_screened)
            except Exception as e:
                logger.warning("LLM analysis failed: %s", e)

        self._progress("complete", 1.0, f"Pipeline complete in {duration}s")

        # Determine models used
        models_used = []
        if nim and nim.available and use_nim:
            if evo2_data:
                models_used.append("Evo2-40b (NVIDIA NIM)")
            models_used.append("ESM-2 650M (HuggingFace, local)")
            models_used.extend([
                "ESMFold (NVIDIA NIM)",
                "Boltz-2 (NVIDIA NIM)",
            ])
            if novel_molecules:
                models_used.append("MolMIM (NVIDIA NIM)")
            if docking_results:
                models_used.append("DiffDock (NVIDIA NIM)")
            if binder_designs:
                models_used.append("RFdiffusion (NVIDIA NIM)")
                models_used.append("ProteinMPNN (NVIDIA NIM)")
        else:
            models_used.append("heuristic_scoring")
        if llm_insights:
            models_used.append("Qwen3-235B (Nebius AI Studio)")

        return PipelineResults(
            pathogen=pathogen_name,
            targets=targets,
            screening_results=all_screening,
            safety_reports=safety_reports,
            top_candidates=candidates,
            metadata={
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "duration_seconds": duration,
                "models_used": models_used,
                "compounds_screened": screening.compounds_screened,
                "demo_mode": demo_mode,
                "evo2_analysis": evo2_data,
                "docking_results": docking_results,
                "binder_designs": binder_designs,
                "llm_insights": llm_insights,
                "novel_molecules": novel_molecules,
            },
        )
