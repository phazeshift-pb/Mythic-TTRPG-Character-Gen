import json
import os
from collections import Counter

import pytest

from src.data_loader import DataLoader
from src.game_data import GameData
from src.validators.base_validator import BaseValidator
from tools import validate_all


@pytest.mark.parametrize("use_lns", [False, True])
def test_loads_cleanly_and_once(use_lns, monkeypatch):
    counts = Counter()
    original = GameData.add_document

    def counting_add(self, family, name, doc):
        counts[doc["source_path"]] += 1
        original(self, family, name, doc)

    monkeypatch.setattr(GameData, "add_document", counting_add)
    game_data = DataLoader(use_light_and_sky=use_lns).load_all()

    assert game_data.errors == []
    assert counts and max(counts.values()) == 1
    assert game_data.list("soldier_type")


def test_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    game_data = DataLoader().load_all()
    assert game_data.errors == []
    assert all(
        doc["source_path"].startswith("data/")
        for family in game_data.families.values()
        for doc in family.values()
    )


def test_duplicate_names_in_a_family_are_reported(tmp_path):
    for folder in ("a", "b"):
        (tmp_path / "core" / folder).mkdir(parents=True)
        (tmp_path / "core" / folder / "skills.json").write_text(json.dumps({"skills": []}))
    game_data = GameData()
    loader = DataLoader(data_root=tmp_path)
    loader._load_folder(loader.core_root, game_data, BaseValidator(game_data))
    assert any("duplicate skills name 'skills'" in e for e in game_data.errors)


def test_skill_characteristics_accept_names_and_codes():
    v = BaseValidator(GameData())
    assert v.characteristic_code("Charisma") == "CHA"
    assert v.characteristic_code("wfm") == "WFM"
    assert v.characteristic_code("Luck") is None


def test_validator_flags_unknown_pack_skill():
    game_data = GameData()
    game_data.add_document(
        "specialization_packs",
        "packs",
        {"specialization_packs": {"standard": [
            {"name": "Bad", "skills": ["Demolitions (Trained)"], "abilities": ["Nope"]}
        ]}},
    )
    errors = []
    validate_all.check_specialization_packs(game_data, {"Demolition"}, set(), errors)
    assert len(errors) == 2


def test_validate_all_passes_on_repo_data(capsys):
    assert validate_all.main([]) == 0
