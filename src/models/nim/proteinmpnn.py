"""ProteinMPNN sequence design mixin."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProteinMPNNResult:
    """Sequence design result for a protein backbone."""
    sequences: list[dict] = field(default_factory=list)
    num_sequences: int = 0
    success: bool = False


class ProteinMPNNMixin:
    """Mixin providing design_sequence() for NIMClient."""

    def design_sequence(self, pdb_structure: str) -> ProteinMPNNResult:
        """Design amino acid sequences for a protein backbone.

        Args:
            pdb_structure: PDB format structure string.

        Returns:
            ProteinMPNNResult with designed sequences and scores.
        """
        try:
            data = self._post("proteinmpnn", {
                "input_pdb": pdb_structure,
            }, timeout=120)
            if isinstance(data, str):
                return ProteinMPNNResult()

            mfasta = data.get("mfasta", "")
            scores = data.get("scores", [])
            seq_list = []

            if mfasta:
                lines = mfasta.strip().split("\n")
                current_header = ""
                current_seq = ""
                for line in lines:
                    if line.startswith(">"):
                        if current_seq:
                            idx = len(seq_list)
                            score = scores[idx] if idx < len(scores) else 0.0
                            seq_list.append({
                                "header": current_header,
                                "sequence": current_seq,
                                "score": score,
                            })
                        current_header = line[1:].strip()
                        current_seq = ""
                    else:
                        current_seq += line.strip()
                if current_seq:
                    idx = len(seq_list)
                    score = scores[idx] if idx < len(scores) else 0.0
                    seq_list.append({
                        "header": current_header,
                        "sequence": current_seq,
                        "score": score,
                    })

            if seq_list:
                return ProteinMPNNResult(
                    sequences=seq_list,
                    num_sequences=len(seq_list),
                    success=True,
                )

            return ProteinMPNNResult()
        except Exception as exc:
            logger.error("ProteinMPNN error: %s", exc)
            return ProteinMPNNResult()
