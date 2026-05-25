#!/usr/bin/env python3
"""Regression tests for quality_lens.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("quality_lens.py")


def run_lens(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["python3", str(SCRIPT), *args, str(root)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def test_quality_lens_summarizes_failure_and_change_pressure() -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
        root = Path(tmp)
        (root / "config_loader.py").write_text(
            """
class ConfigProcessor:
    def processData(self, data):
        return data

def load_config(path):
    try:
        raw = path.read_text()
    except Exception:
        return {}
    result = {}
    if raw:
        result["raw"] = raw
    if "a" in raw:
        result["a"] = True
    if "b" in raw:
        result["b"] = True
    if "c" in raw:
        result["c"] = True
    if "d" in raw:
        result["d"] = True
    if "e" in raw:
        result["e"] = True
    if "f" in raw:
        result["f"] = True
    if "g" in raw:
        result["g"] = True
    if "h" in raw:
        result["h"] = True
    return result
""",
            encoding="utf-8",
        )

        output = run_lens(root)
        assert "Quality lens:" in output
        assert "Failure semantics" in output
        assert "Change shape" in output
        assert "Primary frame:" in output
        assert "Agent mode: lens-first" in output
        assert "Agent protocol:" in output
        assert "silent-fallback" in output


def test_quality_lens_json_accepts_configured_lens_weights() -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
        root = Path(tmp)
        (root / ".llm-code-auditor.json").write_text(
            json.dumps(
                {
                    "generic_suffixes": ["Thingy"],
                    "lens_weights": {
                        "naming-inflation": {
                            "domain-fit": 1.0,
                            "economy": 0.0,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        (root / "sample.py").write_text(
            """
class BillingThingy:
    pass
""",
            encoding="utf-8",
        )

        model = json.loads(run_lens(root, "--json"))
        lenses = {lens["id"]: lens for lens in model["lenses"]}
        assert lenses["domain-fit"]["pressure"] > 0
        assert lenses["economy"]["pressure"] == 0
        assert model["agent_protocol"]["mode"] == "lens-first"
        assert model["agent_protocol"]["inspect"]


if __name__ == "__main__":
    test_quality_lens_summarizes_failure_and_change_pressure()
    test_quality_lens_json_accepts_configured_lens_weights()
