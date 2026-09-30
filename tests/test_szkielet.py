from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_min_start_w_jednym_miejscu():
    cfg = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    assert cfg["data"]["min_start"] == "2021-01-01"


def test_prd_i_zasady_istnieja():
    assert (ROOT / "docs" / "PRD.md").is_file()
    assert "R17" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
