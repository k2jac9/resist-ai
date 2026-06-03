"""Tests for CLI helper utilities (color, table, badge) -- no subprocess needed."""
import os
import sys
from io import StringIO

import pytest


# Force NO_COLOR so ANSI codes are stripped in test output.
os.environ["NO_COLOR"] = "1"


from src.cli import (
    bold,
    dim,
    red,
    green,
    yellow,
    blue,
    cyan,
    mag,
    badge,
    table,
    _load_env,
)


# ---------------------------------------------------------------------------
# ANSI helpers (NO_COLOR=1 → passthrough)
# ---------------------------------------------------------------------------

class TestColorHelpers:
    def test_bold_passthrough(self):
        assert bold("hello") == "hello"

    def test_red_passthrough(self):
        assert red("err") == "err"

    def test_green_passthrough(self):
        assert green("ok") == "ok"

    def test_badge_on(self):
        b = badge("NIM", True)
        assert "NIM" in b
        assert "ON" in b

    def test_badge_off(self):
        b = badge("NIM", False)
        assert "NIM" in b
        assert "OFF" in b


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

class TestTable:
    def test_renders_header_and_rows(self):
        out = table(["Name", "Score"], [["Meropenem", "0.87"], ["Aspirin", "0.45"]])
        assert "Name" in out
        assert "Score" in out
        assert "Meropenem" in out
        assert "Aspirin" in out

    def test_separator_present(self):
        out = table(["A", "B"], [["1", "2"]])
        assert "+" in out
        assert "-" in out

    def test_single_row(self):
        out = table(["Drug"], [["Taniborbactam"]])
        assert "Taniborbactam" in out

    def test_custom_widths(self):
        out = table(["A", "B"], [["x", "y"]], widths=[5, 5])
        # Each cell should be padded to at least width 5
        lines = out.splitlines()
        assert any(len(line) >= 5 for line in lines)

    def test_empty_rows(self):
        out = table(["X", "Y"], [])
        assert "X" in out
        assert "Y" in out


# ---------------------------------------------------------------------------
# _load_env
# ---------------------------------------------------------------------------

class TestLoadEnv:
    def test_missing_env_file_is_silent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _load_env()  # Should not raise

    def test_loads_simple_key_value(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_CLI_VAR=hello_world\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_CLI_VAR", raising=False)
        _load_env()
        assert os.environ.get("TEST_CLI_VAR") == "hello_world"

    def test_ignores_comments(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("# this is a comment\nFOO_CLI=bar\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("FOO_CLI", raising=False)
        _load_env()
        assert os.environ.get("FOO_CLI") == "bar"

    def test_does_not_overwrite_existing_env(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("RESIST_EXISTING=from_file\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("RESIST_EXISTING", "original")
        _load_env()
        assert os.environ.get("RESIST_EXISTING") == "original"
