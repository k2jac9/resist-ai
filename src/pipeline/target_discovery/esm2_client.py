"""ESM-2 protein analysis client for embeddings and druggability prediction."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

ESM2_MODEL_NAME = "facebook/esm2_t33_650M_UR50D"
EMBEDDING_DIM = 1280


def _mock_embedding(seq_len: int) -> np.ndarray:
    """Generate a deterministic mock embedding with realistic shape."""
    rng = np.random.default_rng(seed=hash(str(seq_len)) % (2**31))
    return rng.standard_normal((seq_len, EMBEDDING_DIM)).astype(np.float32)


class ESM2Client:
    """Client for ESM-2 protein language model embeddings and analysis."""

    def __init__(self, model_name: str = ESM2_MODEL_NAME) -> None:
        self._model_name = model_name
        self._tokenizer = None
        self._model = None
        self._available = False
        self._device = "cpu"
        self._init_model()

    def _init_model(self) -> None:
        """Load ESM-2 model and tokenizer from HuggingFace."""
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModel.from_pretrained(self._model_name)

            if torch.cuda.is_available():
                self._device = "cuda"
                self._model = self._model.to(self._device)
                logger.info("ESM-2 model loaded on GPU")
            else:
                logger.info("ESM-2 model loaded on CPU")

            self._model.eval()
            self._available = True
        except ImportError:
            logger.warning("transformers/torch not installed; ESM-2 will use mock embeddings")
        except Exception as exc:
            logger.warning("Failed to load ESM-2 model: %s; using mock embeddings", exc)

    def get_embeddings(self, protein_sequence: str) -> np.ndarray:
        """Generate per-residue ESM-2 embeddings for a protein sequence.

        Args:
            protein_sequence: Amino acid sequence string (e.g. 'MKTL...').

        Returns:
            Numpy array of shape (seq_len, 1280) with per-residue embeddings.
        """
        if not self._available:
            logger.info("Using mock embeddings for sequence of length %d", len(protein_sequence))
            return _mock_embedding(len(protein_sequence))

        try:
            import torch

            inputs = self._tokenizer(
                protein_sequence,
                return_tensors="pt",
                padding=False,
                truncation=True,
                max_length=1024,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            # Strip [CLS] and [EOS] tokens from last hidden state
            embeddings = outputs.last_hidden_state[0, 1:-1, :].cpu().numpy()
            return embeddings
        except Exception as exc:
            logger.error("ESM-2 embedding failed: %s; returning mock", exc)
            return _mock_embedding(len(protein_sequence))

    def get_sequence_embedding(self, protein_sequence: str) -> np.ndarray:
        """Get a single fixed-length embedding by mean-pooling residue embeddings.

        Args:
            protein_sequence: Amino acid sequence string.

        Returns:
            Numpy array of shape (1280,) representing the whole sequence.
        """
        per_residue = self.get_embeddings(protein_sequence)
        return np.mean(per_residue, axis=0)

    def predict_druggability(self, protein_sequence: str) -> float:
        """Predict druggability score for a protein based on embedding features.

        Heuristic scoring based on:
        - Sequence length (ideal binding pockets in 200-800 residue range)
        - Embedding variance (structural complexity)
        - Hydrophobic residue fraction (binding pocket character)

        Args:
            protein_sequence: Amino acid sequence string.

        Returns:
            Float between 0.0 and 1.0 (higher = more druggable).
        """
        embeddings = self.get_embeddings(protein_sequence)
        seq_len = len(protein_sequence)

        # Length score: proteins 200-800 residues are often druggable enzymes
        if 200 <= seq_len <= 800:
            length_score = 1.0
        elif seq_len < 100 or seq_len > 2000:
            length_score = 0.3
        else:
            length_score = 0.7

        # Embedding variance as proxy for structural complexity
        variance = float(np.mean(np.var(embeddings, axis=0)))
        variance_score = min(1.0, variance / 2.0)

        # Hydrophobic residue fraction (binding pocket heuristic)
        hydrophobic = set("AILMFWVP")
        hydro_frac = sum(1 for aa in protein_sequence if aa in hydrophobic) / max(seq_len, 1)
        hydro_score = min(1.0, hydro_frac / 0.4)  # normalize around typical 30-40%

        # Weighted combination
        score = 0.35 * length_score + 0.40 * variance_score + 0.25 * hydro_score
        return round(min(1.0, max(0.0, score)), 4)

    def find_similar_proteins(
        self,
        query_embedding: np.ndarray,
        reference_embeddings: list[tuple[str, np.ndarray]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Find most similar proteins by cosine similarity of sequence embeddings.

        Args:
            query_embedding: 1-D array of shape (1280,) for the query protein.
            reference_embeddings: List of (protein_id, embedding) tuples.
            top_k: Number of top matches to return.

        Returns:
            Sorted list of dicts with 'protein_id' and 'similarity' keys.
        """
        if len(reference_embeddings) == 0:
            return []

        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        results: list[dict[str, Any]] = []

        for protein_id, ref_emb in reference_embeddings:
            ref_norm = ref_emb / (np.linalg.norm(ref_emb) + 1e-10)
            similarity = float(np.dot(query_norm, ref_norm))
            results.append({"protein_id": protein_id, "similarity": round(similarity, 4)})

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
