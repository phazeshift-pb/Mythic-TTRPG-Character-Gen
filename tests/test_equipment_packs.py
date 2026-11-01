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
    index, armors = packs.armory_index(data), packs.armor_index(data)
    for name in data.list("soldier_type"):
        for pack, items in (data.get("soldier_type", name).get("equipment_sets") or {}).items():
            picks = [group["labels"][0] for group in packs.choice_groups(items)]
            contents = packs.resolve_pack(items, picks, index, armors)
            assert contents.problems == [], (name, pack, contents.problems)
            assert all(w["name"] in index for w in contents.weapons)
            assert contents.armor is None or contents.armor in armors
            assert all(isinstance(g, str) for g in contents.equipment)
            # Every non-Spartan pack (except the AI's) now comes with armor.
            if name not in ("spartan_ii", "spartan_iii", "spartan_iv", "smart_ai"):
                assert contents.armor, (name, pack)


def test_marine_point_man_pack():
    data = _core()
    items = data.get("soldier_type", "marine")["equipment_sets"]["point_man"]
    groups = packs.choice_groups(items)
    assert [g["row_label"] for g in groups] == [
        "MA5 Series Assault Rifle",
        "M6 Series Pistol (time period appropriate)",
        "M1 Combat Knife or Model 52 Knife",
        "M50B, M52B, or M53 BDU (time period dependent)",
    ]
    assert groups[-1]["section"] == "armor"
    picks = [
        "MA5C Individual Combat Weapon System",
        "M6D Personal Defense Weapon System",
        "Model 52 Navy Knife",
        "M52B Standard",
    ]
    weapons, armor, gear, problems = packs.resolve_pack(
        items, picks, packs.armory_index(data), packs.armor_index(data)
    )
    assert problems == [] and armor == "M52B Standard"
    assert not any("BDU" in g for g in gear)
    by_name = {w["name"]: w for w in weapons}
    assert set(by_name) == set(picks[:3]) | {"M9 High-Explosive Dual-Purpose Grenade", "Flashbang Grenade"}
    assert by_name["M9 High-Explosive Dual-Purpose Grenade"]["quantity"] == 2
    assert by_name["M6D Personal Defense Weapon System"]["nickname"] == "M6D"
    assert by_name["Flashbang Grenade"]["category"] == "grenades"
    assert "Flashlight" in gear and not any("Grenade" in g for g in gear)


def test_missing_pick_is_reported_not_guessed():
    items = [{"label": "A or B", "choose_one": [{"weapon": "A"}, {"weapon": "B"}]}, "Flashlight"]
    weapons, armor, gear, problems = packs.resolve_pack(items, [])
    assert weapons == [] and armor is None and gear == ["Flashlight"] and len(problems) == 1


def test_spartan_silenced_smgs_keep_quantity_and_note():
    items = _core().get("soldier_type", "spartan_ii")["equipment_sets"]["assault_and_ambush"]
    smg = items[0]
    assert smg == {
        "weapon": "M7 Caseless Submachine Gun",
        "quantity": 2,
        "note": "Silenced",
        "label": "Two M7 Silenced Submachine Guns",
    }
    weapon, = packs.resolve_pack([smg]).weapons
    assert packs.weapon_summary(weapon) == "2x M7 Caseless Submachine Gun [Silenced]"


def test_character_apply_pack_and_sheet_summary():
    data = _core()
    char = CharacterGenerator(data).generate("t", "odst", auto_assign_skills=False)
    items = data.get("soldier_type", "odst")["equipment_sets"]["assault_and_ambush"]
    picks = [g["labels"][0] for g in packs.choice_groups(items)]
    index, armors = packs.armory_index(data), packs.armor_index(data)
    weapons, armor, gear, _ = packs.resolve_pack(items, picks, index, armors)
    char.apply_equipment_pack("assault_and_ambush", gear, weapons, armor)
    assert char.equipment_pack == "assault_and_ambush"
    assert char.armor == "Standard ODST Battle Dress Uniform"
    assert packs.armor_summary(char.armor, armors) == (
        "Standard ODST Battle Dress Uniform - Head 20, Arms 19, Chest 20, Legs 19"
    )
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
        {"armor": "Paper Armor"},
    ]}})
    errors = []
    validate_all.check_equipment_packs(bad, errors)
    assert len(errors) == 5


def test_second_armor_in_a_pack_is_carried_not_worn():
    contents = packs.resolve_pack([{"armor": "A"}, {"armor": "B"}])
    assert contents.armor == "A" and contents.equipment == ["B (spare armor)"]


def test_marine_close_quarters_lists_two_bdus_like_the_book():
    items = _core().get("soldier_type", "marine")["equipment_sets"]["close_quarters"]
    armor_groups = [g for g in packs.choice_groups(items) if g["section"] == "armor"]
    assert len(armor_groups) == 2
