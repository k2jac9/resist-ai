"""Evo2-40b genomic sequence generation mixin."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Evo2Result:
    """Genomic sequence generation result."""
    generated_sequence: str = ""
    input_length: int = 0
    output_length: int = 0
    elapsed_ms: float = 0.0
    success: bool = False


class Evo2Mixin:
    """Mixin providing generate_dna() for NIMClient."""

    def generate_dna(self, sequence: str, num_tokens: int = 256) -> Evo2Result:
        """Generate DNA sequence continuation using Evo2-40b.

        Args:
            sequence: Input DNA sequence (A/T/G/C).
            num_tokens: Number of nucleotide tokens to generate.

        Returns:
            Evo2Result with generated sequence.
        """
        try:
            data = self._post("evo2", {
                "sequence": sequence,
                "num_tokens": num_tokens,
            })
            if isinstance(data, str):
                return Evo2Result(generated_sequence=data, success=bool(data))

            return Evo2Result(
                generated_sequence=data.get("sequence", ""),
                input_length=len(sequence),
                output_length=len(data.get("sequence", "")),
                elapsed_ms=data.get("_elapsed_ms", data.get("elapsed_ms", 0)),
                success=bool(data.get("sequence")),
            )
        except Exception as exc:
            logger.error("Evo2 error: %s", exc)
            return Evo2Result()
