"""Tests for src.cli command handlers, parser, and dispatch."""
import json
from unittest.mock import MagicMock, patch

import pytest

from src import cli


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_build_parser_known_subcommands(self):
        p = cli.build_parser()
        # parse_args needs a subcommand; verify each one is registered
        for cmd in ("run", "predict", "fold", "generate", "dock",
                    "design-binder", "health", "models"):
            ns = p.parse_args([cmd] if cmd not in ("predict", "fold", "generate", "dock", "design-binder")
                              else [cmd, "--sequence", "MKTAYIAKQRQISFVKSHFSRQA", "--smiles", "CCO"]
                              if cmd in ("predict", "dock")
                              else [cmd, "--sequence", "MKTAYIAKQRQISFVKSHFSRQA"]
                              if cmd in ("fold", "design-binder")
                              else [cmd, "--seed", "CCO"])
            assert ns.command == cmd

    def test_run_default_pathogen(self):
        p = cli.build_parser()
        ns = p.parse_args(["run"])
        assert ns.pathogen == "acinetobacter_baumannii"
        assert ns.max_drugs == 100
        assert ns.novel is False

    def test_run_with_novel_flag(self):
        p = cli.build_parser()
        ns = p.parse_args(["run", "--novel", "--max-drugs", "50"])
        assert ns.novel is True
        assert ns.max_drugs == 50

    def test_unknown_command_no_command_attr(self):
        p = cli.build_parser()
        ns = p.parse_args([])
        assert ns.command is None


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    def test_no_command_returns_1(self, capsys):
        rc = cli.main([])
        assert rc == 1
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "command" in out.lower()

    def test_handler_exception_returns_1(self, capsys):
        boom_dispatch = dict(cli._DISPATCH, health=lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
        with patch.object(cli, "_DISPATCH", boom_dispatch):
            rc = cli.main(["health"])
        assert rc == 1
        assert "boom" in capsys.readouterr().out

    def test_handler_exception_json_mode(self, capsys):
        boom_dispatch = dict(cli._DISPATCH, health=lambda _: (_ for _ in ()).throw(RuntimeError("boom")))
        with patch.object(cli, "_DISPATCH", boom_dispatch):
            rc = cli.main(["health", "--json"])
        assert rc == 1
        body = json.loads(capsys.readouterr().out.strip())
        assert body == {"error": "boom"}

    def test_keyboard_interrupt_returns_130(self):
        def _raise(_):
            raise KeyboardInterrupt
        kbd_dispatch = dict(cli._DISPATCH, health=_raise)
        with patch.object(cli, "_DISPATCH", kbd_dispatch):
            rc = cli.main(["health"])
        assert rc == 130


# ---------------------------------------------------------------------------
# cmd_health
# ---------------------------------------------------------------------------


class TestCmdHealth:
    def test_no_api_key_returns_1(self, capsys):
        mock_nim = MagicMock(available=False)
        with patch.object(cli, "_nim", return_value=mock_nim):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_health(MagicMock(json=False))
        assert rc == 1
        assert "NVIDIA_API_KEY" in capsys.readouterr().out

    def test_no_api_key_json_mode(self, capsys):
        mock_nim = MagicMock(available=False)
        with patch.object(cli, "_nim", return_value=mock_nim):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_health(MagicMock(json=True))
        assert rc == 1
        body = json.loads(capsys.readouterr().out.strip())
        assert "error" in body
        assert body["endpoints"] == {}

    def test_healthy_endpoints(self, capsys):
        mock_nim = MagicMock(available=True)
        mock_nim.health_check.return_value = {
            "esmfold": True, "boltz2": True, "molmim": False,
        }
        with patch.object(cli, "_nim", return_value=mock_nim):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_health(MagicMock(json=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "esmfold" in out
        assert "boltz2" in out


# ---------------------------------------------------------------------------
# cmd_models
# ---------------------------------------------------------------------------


class TestCmdModels:
    def test_lists_seven_models(self, capsys):
        with patch.object(cli, "_load_env"):
            rc = cli.cmd_models(MagicMock(json=False))
        assert rc == 0
        out = capsys.readouterr().out
        for name in ("ESMFold", "Evo2-40b", "Boltz-2", "MolMIM",
                     "RFdiffusion", "ProteinMPNN", "DiffDock"):
            assert name in out

    def test_models_json_returns_seven(self, capsys):
        with patch.object(cli, "_load_env"):
            rc = cli.cmd_models(MagicMock(json=True))
        assert rc == 0
        body = json.loads(capsys.readouterr().out.strip())
        assert len(body) == 7
        assert all("name" in m and "key" in m and "url" in m for m in body)


# ---------------------------------------------------------------------------
# cmd_predict
# ---------------------------------------------------------------------------


class TestCmdPredict:
    def test_successful_prediction_returns_0(self, capsys):
        mock_result = MagicMock(
            success=True, confidence_score=0.95, ptm_score=0.88,
            iptm_score=0.85, ligand_iptm_score=0.82,
            complex_plddt=0.91, complex_iplddt=0.89,
        )
        mock_nim = MagicMock()
        mock_nim.predict_binding.return_value = mock_result
        with patch.object(cli, "_nim", return_value=mock_nim):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_predict(MagicMock(
                    sequence="MKTAYIAKQRQISFVKSHFSRQA",
                    smiles="CCO", json=False,
                ))
        assert rc == 0
        out = capsys.readouterr().out
        assert "0.9500" in out

    def test_failed_prediction_returns_1(self, capsys):
        mock_result = MagicMock(success=False)
        mock_nim = MagicMock()
        mock_nim.predict_binding.return_value = mock_result
        with patch.object(cli, "_nim", return_value=mock_nim):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_predict(MagicMock(
                    sequence="MKTAYIAKQRQISFVKSHFSRQA",
                    smiles="CCO", json=False,
                ))
        assert rc == 1


# ---------------------------------------------------------------------------
# cmd_run
# ---------------------------------------------------------------------------


class TestCmdRun:
    def test_run_handles_orchestrator_exception(self, capsys):
        mock_orch = MagicMock()
        mock_orch.run_full_pipeline.side_effect = ValueError("unknown pathogen")
        with patch.object(cli, "_orchestrator", return_value=mock_orch):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_run(MagicMock(
                    pathogen="bogus", max_drugs=10, novel=False, json=False,
                ))
        assert rc == 1
        assert "unknown pathogen" in capsys.readouterr().out

    def test_run_json_output(self, capsys):
        mock_results = MagicMock()
        mock_results.to_dict.return_value = {"pathogen": "test", "targets": []}
        mock_orch = MagicMock()
        mock_orch.run_full_pipeline.return_value = mock_results
        with patch.object(cli, "_orchestrator", return_value=mock_orch):
            with patch.object(cli, "_load_env"):
                rc = cli.cmd_run(MagicMock(
                    pathogen="test", max_drugs=10, novel=False, json=True,
                ))
        assert rc == 0
        out = capsys.readouterr().out
        # cmd_run prints a banner before the JSON payload; locate the JSON object
        json_start = out.index("{")
        body = json.loads(out[json_start:])
        assert body["pathogen"] == "test"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


class TestFormatHelpers:
    def test_table_renders_headers_and_rows(self):
        out = cli.table(["A", "B"], [["1", "2"], ["3", "4"]])
        # ANSI may be off; just verify content
        assert "A" in out
        assert "B" in out
        assert "1" in out
        assert "4" in out

    def test_badge_on_off(self):
        on = cli.badge("test", True)
        off = cli.badge("test", False)
        assert "test" in on
        assert "test" in off
