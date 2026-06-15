"""Tests for the data layer: pathogen metadata and drug library lookups."""
from src.data.drug_library import DrugLibrary
from src.data.pathogens import PathogenManager


class TestPathogenManager:
    def test_list_pathogens_sorted_nonempty(self):
        mgr = PathogenManager()
        listed = mgr.list_pathogens()
        assert listed == sorted(listed)
        assert len(listed) >= 1

    def test_each_listed_pathogen_resolves(self):
        mgr = PathogenManager()
        for key in mgr.list_pathogens():
            data = mgr.get_pathogen(key)
            assert data is not None
            assert "who_priority" in data

    def test_unknown_pathogen_returns_none(self):
        mgr = PathogenManager()
        assert mgr.get_pathogen("not_a_pathogen") is None
        assert mgr.get_who_priority("not_a_pathogen") is None
        assert mgr.get_pdb_codes("not_a_pathogen") == []
        assert mgr.get_uniprot_ids("not_a_pathogen") == []

    def test_critical_pathogens_subset(self):
        mgr = PathogenManager()
        critical = set(mgr.get_critical_pathogens())
        assert critical.issubset(set(mgr.list_pathogens()))
        for key in critical:
            assert mgr.get_who_priority(key) == "critical"

    def test_get_target_missing(self):
        mgr = PathogenManager()
        assert mgr.get_target("not_a_pathogen", "NDM-1") is None


class TestDrugLibrary:
    def test_get_drug_smiles_case_insensitive_fallback(self):
        lib = DrugLibrary()
        # Amoxicillin is in the hardcoded fallback antibiotic set.
        smiles = lib.get_drug_smiles("amOxiCILLin")
        assert smiles
        assert lib.get_drug_smiles("Amoxicillin") == smiles

    def test_unknown_drug_returns_none(self):
        assert DrugLibrary().get_drug_smiles("nonexistent-drug") is None

    def test_index_skips_incomplete_entries(self):
        lib = DrugLibrary()
        lib._index_smiles([
            {"name": "Foo", "smiles": "CCO"},
            {"name": "", "smiles": "CCC"},      # no name -> skipped
            {"name": "Bar", "smiles": ""},       # no smiles -> skipped
        ])
        assert lib.get_drug_smiles("foo") == "CCO"
        assert lib.get_drug_smiles("bar") is None
