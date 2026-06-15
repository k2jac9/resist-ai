"""Tests for Tanimoto similarity search and Butina clustering."""
from src.pipeline.drug_screening.similarity_search import (
    cluster_hits,
    find_similar_drugs,
)

ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"
LIBRARY = [
    {"name": "Aspirin", "smiles": ASPIRIN},
    {"name": "Ethanol", "smiles": "CCO"},
    {"name": "Salicylic acid", "smiles": "O=C(O)c1ccccc1O"},
    {"name": "NoSmiles"},  # skipped
]


class TestFindSimilarDrugs:
    def test_identical_ranks_first_with_sim_one(self):
        results = find_similar_drugs(ASPIRIN, LIBRARY, top_k=3)
        assert results[0]["name"] == "Aspirin"
        assert results[0]["similarity"] == 1.0
        # sorted descending
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_skips_entries_without_smiles(self):
        names = {r["name"] for r in find_similar_drugs(ASPIRIN, LIBRARY, top_k=10)}
        assert "NoSmiles" not in names

    def test_invalid_query_returns_empty(self):
        assert find_similar_drugs("NOT_A_MOLECULE!!!", LIBRARY) == []

    def test_top_k_limits_results(self):
        assert len(find_similar_drugs(ASPIRIN, LIBRARY, top_k=2)) == 2


class TestClusterHits:
    def test_empty_returns_empty(self):
        assert cluster_hits([]) == []

    def test_returns_clusters_covering_all_valid_hits(self):
        hits = [{"smiles": ASPIRIN}, {"smiles": "O=C(O)c1ccccc1O"}, {"smiles": "CCO"}]
        clusters = cluster_hits(hits, threshold=0.7)
        flattened = [h for c in clusters for h in c]
        assert len(flattened) == len(hits)
        # clusters sorted largest-first
        assert all(len(clusters[i]) >= len(clusters[i + 1]) for i in range(len(clusters) - 1))
