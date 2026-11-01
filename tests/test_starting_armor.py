"""Spartans choose a starting Mjolnir/SPI suit and an optional variant."""
from src.data_loader import DataLoader
from src.game_data import GameData
from src.models import starting_armor as sa
from src.models.equipment_packs import armor_index
from tools import validate_all


def _core():
    return DataLoader().load_all()


def test_only_spartans_have_starting_armor_choices():
    data = _core()
    with_options = {n for n in data.list("soldier_type") if sa.armor_options(data.get("soldier_type", n))}
    assert with_options == {"spartan_ii", "spartan_iii", "spartan_iv"}
    labels = [o["label"] for o in sa.armor_options(data.get("soldier_type", "spartan_ii"))]
    assert labels[0] == "SPI Mark I (2531–2537)" and labels[-1] == "GEN III Mjolnir (2559+)"


def test_variants_follow_each_suits_generations():
    data = _core()
    armors = armor_index(data)
    mk4 = sa.variants_for(armors["Mark IV Powered Assault Armor"], data)
    gen2 = sa.variants_for(armors["GEN II Powered Armor"], data)
    gen3 = sa.variants_for(armors["GEN III Powered Armor"], data)
    spi = sa.variants_for(armors["Mark I Semi-Powered Infiltration Armor"], data)
    assert {v["generation"] for v in mk4} == {"GEN I"} and len(mk4) == 32
    assert {v["generation"] for v in gen2} == {"GEN I", "GEN II"} and len(gen2) == 32 + 72
    assert {v["generation"] for v in gen3} == {"GEN I", "GEN II", "GEN III"}
    assert not any(v["name"] == "Default Armors" for v in gen3)
    assert spi == []


def test_worn_bonus_includes_spartan_iv_gen_ii_bonus():
    data = _core()
    armors = armor_index(data)
    s2, s4 = data.get("soldier_type", "spartan_ii"), data.get("soldier_type", "spartan_iv")
    assert sa.worn_bonus("GEN II Powered Armor", s2, armors) == {
        "STR": 20, "mythic_STR": 4, "AGI": 15, "mythic_AGI": 4}
    assert sa.worn_bonus("GEN II Powered Armor", s4, armors) == {
        "STR": 25, "mythic_STR": 4, "TOU": 5, "AGI": 20, "mythic_AGI": 4}
    assert sa.worn_bonus("Mark VI Powered Assault Armor", s4, armors)["STR"] == 20
    assert sa.worn_bonus("ODST UNSC Black Body Suit", s4, armors) == {}
    assert sa.format_bonus({"STR": 20, "mythic_STR": 3}) == "+20 STR, +3 Mythic STR"


def test_validate_choice():
    data = _core()
    armors = armor_index(data)
    s3 = data.get("soldier_type", "spartan_iii")
    recon_gen2 = sa.variant_entry(sa.find_variant(data, "GEN II", "Recon"))
    assert recon_gen2 == {"name": "Recon", "generation": "GEN II", "price": recon_gen2["price"]}
    assert sa.validate_choice(s3, "GEN II Powered Armor", recon_gen2, armors, data) == []
    assert sa.validate_choice(s3, "Mark V Powered Assault Armor", recon_gen2, armors, data)
    assert sa.validate_choice(s3, "M52B Standard", None, armors, data)


def test_character_records_suit_variant_and_bonus():
    from src.generator.character_generator import CharacterGenerator

    data = _core()
    armors = armor_index(data)
    s4 = data.get("soldier_type", "spartan_iv")
    char = CharacterGenerator(data).generate("t", "spartan_iv", auto_assign_skills=False)
    base = dict(char.characteristics)
    variant = sa.variant_entry(sa.find_variant(data, "GEN III", "Argus"))
    char.apply_starting_armor("GEN III Powered Armor", variant, sa.worn_bonus("GEN III Powered Armor", s4, armors))
    assert char.armor == "GEN III Powered Armor"
    assert char.armor_variant["name"] == "Argus"
    assert char.armor_bonus["STR"] == 25
    assert char.characteristics == base  # bonuses are shown, not baked into base stats


def test_validator_flags_bad_starting_armor():
    data = _core()
    bad = GameData()
    bad.families = {"unsc_armor": data.families["unsc_armor"]}
    bad.add_document("soldier_type", "x", {"special_rules": {"mjolnir_armor": {
        "armor_options": [{"armor": "Mark IV Powered Assault Armor"}, {"armor": "Cardboard"}],
        "bonus_while_worn": {"armor": ["Nope"], "characteristics": {"LUCK": 5}},
    }}})
    errors = []
    validate_all.check_starting_armor_options(bad, errors)
    assert len(errors) == 3
