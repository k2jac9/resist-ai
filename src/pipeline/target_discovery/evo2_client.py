"""DEPRECATED Evo2 genomic model client via Nebius AI Studio API.

This module is kept for reference only. It attempts to drive Evo2-40b through
Nebius AI Studio's OpenAI-compatible chat completions endpoint, which is a
misuse of the model (Evo2 is a genomic sequence generator, not a chat model).

Use `src.models.nim_client.NIMClient` with the NVIDIA NIM Evo2 generate endpoint
instead — it is the real, supported integration used by `src.pipeline.stages`
and `src.pipeline.orchestrator`.
"""

from __future__ import annotations

import json
import logging
import os
import warnings
from dataclasses import dataclass

logger = logging.getLogger(__name__)

warnings.warn(
    "src.pipeline.target_discovery.evo2_client is deprecated and will be removed. "
    "Use src.models.nim_client.NIMClient (NVIDIA NIM Evo2 generate endpoint) instead.",
    DeprecationWarning,
    stacklevel=2,
)

NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
EVO2_MODEL = "evo2-40b"


@dataclass
class ResistanceGene:
    """A detected antimicrobial resistance gene."""

    gene_name: str
    gene_family: str
    mechanism: str
    drug_class: str
    confidence: float
    position_start: int = 0
    position_end: int = 0
    notes: str = ""


def _get_mock_resistance_genes() -> list[dict]:
    """Return realistic mock resistance gene findings for A. baumannii."""
    return [
        {
            "gene_name": "blaOXA-23",
            "gene_family": "OXA beta-lactamase",
            "mechanism": "Antibiotic inactivation (hydrolysis)",
            "drug_class": "Carbapenems",
            "confidence": 0.97,
            "position_start": 14520,
            "position_end": 15341,
            "notes": "Class D carbapenemase; most prevalent in CRAB",
        },
        {
            "gene_name": "blaNDM-1",
            "gene_family": "NDM beta-lactamase",
            "mechanism": "Antibiotic inactivation (metallo-beta-lactamase)",
            "drug_class": "Carbapenems, Cephalosporins",
            "confidence": 0.95,
            "position_start": 28710,
            "position_end": 29522,
            "notes": "Metallo-beta-lactamase requiring zinc cofactors",
        },
        {
            "gene_name": "adeB",
            "gene_family": "RND efflux pump",
            "mechanism": "Antibiotic efflux",
            "drug_class": "Aminoglycosides, Fluoroquinolones, Tetracyclines",
            "confidence": 0.91,
            "position_start": 45200,
            "position_end": 48350,
            "notes": "Inner membrane transporter of AdeABC efflux system",
        },
        {
            "gene_name": "armA",
            "gene_family": "16S rRNA methyltransferase",
            "mechanism": "Target modification",
            "drug_class": "Aminoglycosides",
            "confidence": 0.88,
            "position_start": 61430,
            "position_end": 62190,
            "notes": "Confers high-level resistance to gentamicin and amikacin",
        },
        {
            "gene_name": "sul1",
            "gene_family": "Sulfonamide resistant dihydropteroate synthase",
            "mechanism": "Target replacement",
            "drug_class": "Sulfonamides",
            "confidence": 0.85,
            "position_start": 73100,
            "position_end": 73920,
            "notes": "Often found on class 1 integrons",
        },
    ]


def _get_mock_genome_analysis() -> dict:
    """Return mock genome analysis results."""
    return {
        "model": EVO2_MODEL,
        "status": "demo_mode",
        "organism": "Acinetobacter baumannii",
        "sequence_length": 3976747,
        "gc_content": 0.390,
        "predicted_coding_regions": 3681,
        "resistance_islands": 3,
        "genomic_islands": [
            {"name": "AbaR1-like", "start": 14000, "end": 86000, "type": "resistance"},
            {"name": "ICEAba1", "start": 120000, "end": 165000, "type": "integrative_conjugative"},
            {"name": "prophage_Ab1", "start": 230000, "end": 268000, "type": "prophage"},
        ],
        "summary": (
            "Detected multiple resistance determinants typical of multidrug-resistant "
            "A. baumannii, including class D OXA-type carbapenemases and RND efflux systems."
        ),
    }


class Evo2Client:
    """Client for Evo2-40b genomic analysis via Nebius AI Studio."""

    def __init__(self, base_url: str = NEBIUS_BASE_URL, api_key: str | None = None) -> None:
        self._base_url = base_url
        self._api_key = api_key or os.environ.get("NEBIUS_API_KEY", "")
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the OpenAI-compatible client for Nebius."""
        if not self._api_key:
            logger.warning("NEBIUS_API_KEY not set; Evo2 client will use demo mode")
            return
        try:
            from openai import OpenAI

            self._client = OpenAI(base_url=self._base_url, api_key=self._api_key)
            self._available = True
            logger.info("Evo2 client initialized with Nebius AI Studio")
        except ImportError:
            logger.warning("openai package not installed; Evo2 client will use demo mode")
        except Exception as exc:
            logger.warning("Failed to initialize Evo2 client: %s", exc)

    def analyze_genome(self, sequence: str) -> dict:
        """Send a genomic DNA sequence to Evo2-40b for analysis.

        Args:
            sequence: Nucleotide sequence string (A/T/G/C).

        Returns:
            Analysis results including coding regions, islands, and summary.
        """
        if not self._available or not self._client:
            logger.info("Using demo mode for genome analysis")
            return _get_mock_genome_analysis()

        try:
            prompt = (
                "Analyze this bacterial genomic DNA sequence for resistance elements, "
                "coding regions, and genomic islands. Return structured JSON.\n\n"
                f"Sequence (first 2000 bp): {sequence[:2000]}"
            )
            response = self._client.chat.completions.create(
                model=EVO2_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"model": EVO2_MODEL, "raw_response": content}
        except Exception as exc:
            logger.error("Evo2 API call failed: %s; falling back to demo data", exc)
            return _get_mock_genome_analysis()

    def identify_resistance_genes(self, sequence: str) -> list[dict]:
        """Analyze a genomic sequence for antimicrobial resistance gene signatures.

        Args:
            sequence: Nucleotide sequence string.

        Returns:
            List of detected resistance genes with metadata.
        """
        if not self._available or not self._client:
            logger.info("Using demo mode for resistance gene identification")
            return _get_mock_resistance_genes()

        try:
            prompt = (
                "Identify antimicrobial resistance genes in this DNA sequence. "
                "For each gene return: gene_name, gene_family, mechanism, drug_class, "
                "confidence (0-1), position_start, position_end. Return JSON array.\n\n"
                f"Sequence (first 2000 bp): {sequence[:2000]}"
            )
            response = self._client.chat.completions.create(
                model=EVO2_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            try:
                result = json.loads(content)
                return result if isinstance(result, list) else [result]
            except json.JSONDecodeError:
                logger.warning("Could not parse Evo2 response as JSON; using demo data")
                return _get_mock_resistance_genes()
        except Exception as exc:
            logger.error("Evo2 resistance gene call failed: %s; using demo data", exc)
            return _get_mock_resistance_genes()
