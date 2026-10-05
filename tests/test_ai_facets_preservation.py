import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ai_atlas" / "derive_facets.py"
SPEC = importlib.util.spec_from_file_location("derive_facets", SCRIPT)
derive_facets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(derive_facets)


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def setup_files(tmp_path, monkeypatch, row):
    cards = tmp_path / "cards.jsonl"
    items = tmp_path / "items.json"
    backup = tmp_path / "old-backup.jsonl"
    write_jsonl(cards, [row])
    write_jsonl(backup, [{"k": "old-backup-card", "deep": {"look_close": "lava"}}])
    items.write_text(json.dumps([{"k": row["k"], "n": ""}]), encoding="utf-8")
    monkeypatch.setattr(derive_facets, "CARDS", str(cards))
    monkeypatch.setattr(derive_facets, "ITEMS", str(items))
    monkeypatch.setattr(derive_facets, "BAK", str(backup))
    return cards


def read_cards(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_write_preserves_current_edits_and_manual_equal_tag_synonyms(tmp_path, monkeypatch):
    row = {
        "k": "current-card",
        "deep": {"look_close": "A wet finish with amber ember flecks", "manual_note": "keep"},
        "syn": ["ember", "owner phrase"],
        "custom": {"kept": True},
    }
    cards = setup_files(tmp_path, monkeypatch, row)

    derive_facets.main(["--write"])
    result = read_cards(cards)[0]

    assert result["deep"] == row["deep"]
    assert result["custom"] == row["custom"]
    assert result["facets"] == ["ember", "wet"]
    assert result["syn"] == ["ember", "owner phrase", "wet"]


def test_changed_description_removes_only_tracked_generated_synonyms(tmp_path, monkeypatch):
    row = {"k": "current-card", "deep": {"look_close": "wet ember"}, "syn": ["ember", "manual"]}
    cards = setup_files(tmp_path, monkeypatch, row)

    derive_facets.main(["--write"])
    updated = read_cards(cards)[0]
    updated["deep"]["look_close"] = "wood grain"
    write_jsonl(cards, [updated])
    derive_facets.main(["--write"])
    result = read_cards(cards)[0]

    assert result["facets"] == ["wood"]
    assert result["syn"] == ["ember", "manual", "wood"]
    assert result[derive_facets.PROVENANCE] == {"syn": ["wood"]}


def test_write_is_idempotent_and_dry_run_does_not_write(tmp_path, monkeypatch):
    row = {"k": "current-card", "deep": {"look_close": "wet"}, "syn": ["manual"]}
    cards = setup_files(tmp_path, monkeypatch, row)
    original = cards.read_bytes()

    derive_facets.main([])
    assert cards.read_bytes() == original

    derive_facets.main(["--write"])
    once = cards.read_bytes()
    derive_facets.main(["--write"])
    assert cards.read_bytes() == once


def test_first_write_backs_up_current_cards_including_new_cards(tmp_path, monkeypatch):
    cards = tmp_path / "cards.jsonl"
    backup = tmp_path / "cards.before_facets_20261003.jsonl"
    items = tmp_path / "items.json"
    rows = [
        {"k": "old-card", "deep": {"look_close": "wet"}},
        {"k": "new-card", "deep": {"look_close": "wood grain"}, "extra": "preserve"},
    ]
    write_jsonl(cards, rows)
    current_bytes = cards.read_bytes()
    write_jsonl(backup, [{"k": "old-card", "deep": {"look_close": "lava"}}])
    backup.unlink()
    items.write_text(json.dumps([{"k": row["k"], "n": ""} for row in rows]), encoding="utf-8")
    monkeypatch.setattr(derive_facets, "CARDS", str(cards))
    monkeypatch.setattr(derive_facets, "ITEMS", str(items))
    monkeypatch.setattr(derive_facets, "BAK", str(backup))

    derive_facets.main(["--write"])

    assert backup.read_bytes() == current_bytes
    result = read_cards(cards)
    assert [row["k"] for row in result] == ["old-card", "new-card"]
    assert result[1]["extra"] == "preserve"
    assert result[1]["facets"] == ["wood"]
