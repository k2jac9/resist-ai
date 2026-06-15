"""Tests for the settings singleton and dotted-key accessor."""
from src.utils.config import get_settings


def test_singleton_identity():
    assert get_settings() is get_settings()


def test_get_dotted_key_resolves():
    s = get_settings()
    # app.name is always present in settings.yaml
    assert s.get("app.name") == s.app_name


def test_get_missing_returns_default():
    s = get_settings()
    assert s.get("does.not.exist", "fallback") == "fallback"
    assert s.get("app.nope.deeper", 42) == 42


def test_get_default_is_none():
    assert get_settings().get("totally.absent") is None


def test_core_properties_have_values():
    s = get_settings()
    assert isinstance(s.app_name, str) and s.app_name
    assert isinstance(s.app_version, str) and s.app_version
    assert isinstance(s.eskape_pathogens, dict) and s.eskape_pathogens


def test_structures_dir_exists():
    path = get_settings().structures_dir
    assert path.exists() and path.is_dir()
