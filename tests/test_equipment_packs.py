"""Soldier-type equipment packs link to the UNSC Armory."""
from src.data_loader import DataLoader
from src.game_data import GameData
from src.generator.character_generator import CharacterGenerator
from src.models import equipment_packs as packs
from tools import validate_all


def _core():
    return DataLoader().load_all()


def test_every_core_pack_resolves_with_default_picks():
    data = _core()
    index = packs.armory_index(data)
    for name in data.list("soldier_type"):
        for pack, items in (data.get("soldier_type", name).get("equipment_sets") or {}).items():
            picks = [group["labels"][0] for group in packs.choice_groups(items)]
            weapons, gear, problems = packs.resolve_pack(items, picks, index)
            assert problems == [], (name, pack, problems)
            assert all(w["name"] in index for w in weapons)
            assert all(isinstance(g, str) for g in gear)


def test_marine_point_man_pack():
    data = _core()
    items = data.get("soldier_type", "marine")["equipment_sets"]["point_man"]
    groups = packs.choice_groups(items)
    assert [g["row_label"] for g in groups] == [
        "MA5 Series Assault Rifle",
        "M6 Series Pistol (time period appropriate)",
        "M1 Combat Knife or Model 52 Knife",
    ]
    picks = [
        "MA5C Individual Combat Weapon System",
        "M6D Personal Defense Weapon System",
        "Model 52 Navy Knife",
    ]
    weapons, gear, problems = packs.resolve_pack(items, picks, packs.armory_index(data))
    assert problems == []
    by_name = {w["name"]: w for w in weapons}
    assert set(by_name) == set(picks) | {"M9 High-Explosive Dual-Purpose Grenade", "Flashbang Grenade"}
    assert by_name["M9 High-Explosive Dual-Purpose Grenade"]["quantity"] == 2
    assert by_name["M6D Personal Defense Weapon System"]["nickname"] == "M6D"
    assert by_name["Flashbang Grenade"]["category"] == "grenades"
    assert "Flashlight" in gear and not any("Grenade" in g for g in gear)


def test_missing_pick_is_reported_not_guessed():
    items = [{"label": "A or B", "choose_one": [{"weapon": "A"}, {"weapon": "B"}]}, "Flashlight"]
    weapons, gear, problems = packs.resolve_pack(items, [])
    assert weapons == [] and gear == ["Flashlight"] and len(problems) == 1


def test_spartan_silenced_smgs_keep_quantity_and_note():
    items = _core().get("soldier_type", "spartan_ii")["equipment_sets"]["assault_and_ambush"]
    smg = items[0]
    assert smg == {
        "weapon": "M7 Caseless Submachine Gun",
        "quantity": 2,
        "note": "Silenced",
        "label": "Two M7 Silenced Submachine Guns",
    }
    weapon, = packs.resolve_pack([smg])[0]
    assert packs.weapon_summary(weapon) == "2x M7 Caseless Submachine Gun [Silenced]"


def test_character_apply_pack_and_sheet_summary():
    data = _core()
    char = CharacterGenerator(data).generate("t", "odst", auto_assign_skills=False)
    items = data.get("soldier_type", "odst")["equipment_sets"]["assault_and_ambush"]
    picks = [g["labels"][0] for g in packs.choice_groups(items)]
    index = packs.armory_index(data)
    weapons, gear, _ = packs.resolve_pack(items, picks, index)
    char.apply_equipment_pack("assault_and_ambush", gear, weapons)
    assert char.equipment_pack == "assault_and_ambush"
    assert [w["name"] for w in char.weapons][:2] == [
        "M7 Caseless Submachine Gun",
        "M6J Adjustable Personal Defense Carbine",
    ]
    summary = packs.weapon_summary(char.weapons[0], index)
    assert summary == "M7 Caseless Submachine Gun (SMG) - 3D10+1, Pierce 11, 20m-75m, Semi-Auto (3), Auto (10)"


def test_validator_flags_bad_pack_references():
    data = _core()
    bad = GameData()
    bad.families = {k: v for k, v in data.families.items() if k in packs.ARMORY_FAMILIES}
    bad.add_document("soldier_type", "x", {"equipment_sets": {"p": [
        {"weapon": "Not A Gun"},
        {"choose_one": [{"weapon": "M1 Combat Knife"}]},
        {"weapon": "M1 Combat Knife", "quantity": 0},
        {"thing": 1},
    ]}})
    errors = []
    validate_all.check_equipment_packs(bad, errors)
    assert len(errors) == 4
