#!/usr/bin/env python3
"""Regression tests for code_remodel.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("code_remodel.py")


def run_remodel(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["python3", str(SCRIPT), *args, str(root)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def test_remodel_markup_surfaces_structure_without_editing_code() -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
        root = Path(tmp)
        (root / "config_loader.py").write_text(
            """
class ConfigManager:
    def processData(self, data):
        return ConfigProcessor().processData(data)

class ConfigProcessor:
    def processData(self, data):
        try:
            if data.get("a"):
                return {"a": True}
            if data.get("b"):
                return {"b": True}
            if data.get("c"):
                return {"c": True}
            if data.get("d"):
                return {"d": True}
            if data.get("e"):
                return {"e": True}
            if data.get("f"):
                return {"f": True}
            if data.get("g"):
                return {"g": True}
            if data.get("h"):
                return {"h": True}
            return data
        except Exception:
            return {}

def load_config(data):
    return ConfigManager().processData(data)
""",
            encoding="utf-8",
        )

        output = run_remodel(root)
        assert "@remodel version=3 format=compact" in output
        assert "human feedback outranks static leads" in output
        assert "@refactor_guide" in output
        assert "Refactoring Guru" in output
        assert "Martin Fowler" in output
        assert "@concept_map" in output
        assert "Agent" not in output
        assert "unowned-forwarder" in output
        assert "silent-boundary" in output
        assert "branch-hub" in output
        assert "@refactor_moves" in output
        assert "Extract Function" in output
        assert "Inline Function/Method" in output
        assert "@remodel_passes" in output
        assert 'source="human-feedback"' in output
        assert 'source="static-leads"' in output
        assert "@remodel_questions" in output


def test_remodel_json_keeps_domain_named_boundaries_from_being_generic() -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
        root = Path(tmp)
        (root / "checkout.ts").write_text(
            """
class CheckoutService {
  processData(data) {
    return data
  }
}
""",
            encoding="utf-8",
        )

        model = json.loads(run_remodel(root, "--json"))
        symbols = model["symbols"]
        assert symbols[0]["name"] == "CheckoutService"
        assert symbols[0]["role"] == "named-boundary"
        assert not model["friction"]["generic_boundaries"]
        assert model["guide_sources"]
        assert "refactor_moves" in model


def test_remodel_json_reports_generic_symbols_without_domain_concepts() -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
        root = Path(tmp)
        (root / "processor.ts").write_text(
            """
class DataProcessor {
  processData(data) {
    return data
  }
}
""",
            encoding="utf-8",
        )

        model = json.loads(run_remodel(root, "--json"))
        symbols = model["symbols"]
        assert symbols[0]["name"] == "DataProcessor"
        assert symbols[0]["role"] == "generic-symbol"
        assert model["friction"]["generic_boundaries"]


if __name__ == "__main__":
    test_remodel_markup_surfaces_structure_without_editing_code()
    test_remodel_json_keeps_domain_named_boundaries_from_being_generic()
    test_remodel_json_reports_generic_symbols_without_domain_concepts()
