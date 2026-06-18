"""Chemical similarity search and clustering for AMR-AI drug screening.

Uses Tanimoto similarity on Morgan fingerprints (via RDKit) to find
structurally related drugs and group screening hits into clusters.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.utils.chemistry import RDKIT_AVAILABLE

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem
    from rdkit.ML.Cluster import Butina
except ImportError:
    pass  # RDKIT_AVAILABLE already False from chemistry module


# ---------------------------------------------------------------------------
# Fingerprint helpers
# ---------------------------------------------------------------------------

def _morgan_fp(smiles: str, radius: int = 2, n_bits: int = 2048) -> Optional[object]:
    """Compute a Morgan fingerprint bit vector for a SMILES string."""
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def _tanimoto(fp1: object, fp2: object) -> float:
    """Return the Tanimoto similarity between two fingerprints."""
    if fp1 is None or fp2 is None:
        return 0.0
    return float(DataStructs.TanimotoSimilarity(fp1, fp2))


# ---------------------------------------------------------------------------
# Similarity search
# ---------------------------------------------------------------------------

def find_similar_drugs(
    query_smiles: str,
    drug_library: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """Find the most structurally similar drugs to a query molecule.

    Args:
        query_smiles: SMILES string for the query compound.
        drug_library: List of dicts, each with at least a ``smiles`` key.
            May also contain ``name``, ``chembl_id``, etc.
        top_k: Number of top similar drugs to return.

    Returns:
        List of drug dicts augmented with a ``similarity`` score,
        sorted descending by similarity.
    """
    if not RDKIT_AVAILABLE:
        logger.warning("RDKit unavailable; returning first %d drugs unsorted", top_k)
        results: list[dict] = []
        for drug in drug_library[:top_k]:
            entry = dict(drug)
            entry["similarity"] = 0.0
            results.append(entry)
        return results

    query_fp = _morgan_fp(query_smiles)
    if query_fp is None:
        logger.error("Invalid query SMILES: %s", query_smiles)
        return []

    scored: list[tuple[float, dict]] = []
    for drug in drug_library:
        smiles = drug.get("smiles", "")
        if not smiles:
            continue
        drug_fp = _morgan_fp(smiles)
        if drug_fp is None:
            continue
        sim = _tanimoto(query_fp, drug_fp)
        scored.append((sim, drug))

    scored.sort(key=lambda t: t[0], reverse=True)

    results = []
    for sim, drug in scored[:top_k]:
        entry = dict(drug)
        entry["similarity"] = round(sim, 4)
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def cluster_hits(
    hits: list[dict],
    threshold: float = 0.7,
) -> list[list[dict]]:
    """Group hits into clusters based on Tanimoto similarity.

    Uses Butina clustering (Taylor-Butina algorithm) when RDKit is
    available.  Falls back to single-element clusters otherwise.

    Args:
        hits: List of dicts, each with a ``smiles`` key.
        threshold: Tanimoto distance cutoff (1 - similarity).
            Default 0.7 means molecules with >=0.3 similarity cluster.

    Returns:
        List of clusters, each cluster a list of drug dicts.
        Clusters are sorted largest-first.
    """
    if not hits:
        return []

    if not RDKIT_AVAILABLE:
        return [[h] for h in hits]

    # Build fingerprints, skipping invalid SMILES
    fps: list[object] = []
    valid_hits: list[dict] = []
    for hit in hits:
        fp = _morgan_fp(hit.get("smiles", ""))
        if fp is not None:
            fps.append(fp)
            valid_hits.append(hit)

    if not fps:
        return [[h] for h in hits]

    # Compute pairwise distance matrix (upper triangle)
    n = len(fps)
    dists: list[float] = []
    for i in range(1, n):
        for j in range(i):
            dists.append(1.0 - _tanimoto(fps[i], fps[j]))

    # Butina clustering
    clusters_idx = Butina.ClusterData(dists, n, threshold, isDistData=True)

    clusters: list[list[dict]] = []
    for idx_tuple in clusters_idx:
        cluster = [valid_hits[i] for i in idx_tuple]
        clusters.append(cluster)

    # Sort clusters largest-first
    clusters.sort(key=len, reverse=True)
    return clusters
