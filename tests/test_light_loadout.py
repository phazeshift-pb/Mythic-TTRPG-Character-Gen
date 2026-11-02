"""Light & Sky loadout: slots, equipping, and Light/Super Energy."""
import pytest

from src.data_loader import DataLoader
from src.models.light_loadout import LightLoadout


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


def titan(**extra):
    character = {
        "soldier_type": "Titan Class Soldier Type",
        "connections": ["Arc"],
        "light_aspects": ["Ionic Trace"],
        "light_abilities": ["Thruster"],
        "light_grenades": ["Pulse Grenade"],
        "supers": ["Fists of Havoc"],
    }
    character.update(extra)
    return character


def test_old_character_fills_slots_in_order(lns_data):
    state = LightLoadout(titan(), lns_data).loadout()
    assert (state["aspects"], state["abilities"], state["super"]) == (
        ["Ionic Trace"],
        ["Thruster", "Pulse Grenade"],
        "Fists of Havoc",
    )


def test_every_slot_is_listed_and_unbought_ones_are_locked(lns_data):
    loadout = LightLoadout(titan(), lns_data)
    aspects = loadout.slots("aspect")
    assert [slot.unlocked for slot in aspects] == [True, False, False, False]
    assert [slot.unlock_cost for slot in aspects[1:]] == [200, 400, 800]
    assert aspects[1].unlock_note == "" and aspects[2].unlock_note
    abilities = loadout.slots("ability")
    assert [slot.unlocked for slot in abilities] == [True, True, False, False, False]
    assert all(slot.unlock_cost == 500 for slot in abilities[2:])
    assert len(loadout.slots("super")) == 1


def test_bought_slots_unlock(lns_data):
    character = titan(light_aspect_slots_purchased=1, light_ability_slots_purchased=3)
    loadout = LightLoadout(character, lns_data)
    assert [slot.unlocked for slot in loadout.slots("aspect")] == [True, True, False, False]
    assert all(slot.unlocked for slot in loadout.slots("ability"))
    assert len(loadout.slots("ability")) == 5


def test_warlock_gets_an_extra_ability_slot_within_the_same_maximum(lns_data):
    loadout = LightLoadout(titan(soldier_type="Warlock Class Soldier Type"), lns_data)
    abilities = loadout.slots("ability")
    assert [slot.unlocked for slot in abilities] == [True, True, True, False, False, False]


def test_equip_moves_and_empties(lns_data):
    character = titan(light_abilities=["Thruster", "Ballistic Slam"], light_ability_slots_purchased=1)
    loadout = LightLoadout(character, lns_data)
    assert loadout.loadout()["abilities"] == ["Thruster", "Ballistic Slam", "Pulse Grenade"]
    loadout.equip("ability", 3, "Thruster")
    assert character["light_loadout"]["abilities"] == [None, "Ballistic Slam", "Thruster"]
    loadout.equip("ability", 2, None)
    assert loadout.available_for("ability", 1) == ["Ballistic Slam", "Pulse Grenade"]
    with pytest.raises(ValueError):
        loadout.equip("ability", 4, "Thruster")  # locked
    with pytest.raises(ValueError):
        loadout.equip("ability", 1, "Not Owned")


def test_saved_loadout_drops_powers_no_longer_owned(lns_data):
    seen = ["Ionic Trace", "Thruster", "Pulse Grenade", "Fists of Havoc"]
    character = titan(
        light_loadout={"aspects": ["Gone"], "abilities": ["Thruster"], "super": "Gone", "seen": seen}
    )
    state = LightLoadout(character, lns_data).loadout()
    assert (state["aspects"], state["abilities"], state["super"]) == ([None], ["Thruster", None], None)


def test_newly_bought_powers_drop_into_empty_slots_but_removed_ones_stay_out(lns_data):
    character = titan()
    loadout = LightLoadout(character, lns_data)
    loadout.equip("ability", 2, None)  # player takes Pulse Grenade out
    character["light_abilities"].append("Ballistic Slam")  # bought in the XP Shop
    character["supers"].append("Thundercrash")
    state = LightLoadout(character, lns_data).loadout()
    assert state["abilities"] == ["Thruster", "Ballistic Slam"]
    assert state["super"] == "Fists of Havoc"  # one Super at a time; the active one stays


def test_power_details(lns_data):
    loadout = LightLoadout(titan(), lns_data)
    grenade = loadout.power("Pulse Grenade")
    assert grenade.kind == "Light Grenade" and grenade.stats
    thruster = loadout.power("Thruster")
    cost = thruster.energy_cost()
    assert cost is not None and thruster.energy_cost(as_super=True) == cost * 2
    assert loadout.power("Ionic Trace").kind == "Light Aspect"
    assert loadout.power("Light Weapon").energy_text() == "X Light Energy"


def test_energy_defaults_full_clamps_and_spends(lns_data):
    character = titan()
    loadout = LightLoadout(character, lns_data)
    assert loadout.energy("light") == 100 and loadout.energy("super") == 100
    assert loadout.spend("light", 30) and loadout.energy("light") == 70
    assert not loadout.spend("super", 150) and loadout.energy("super") == 100
    assert loadout.gain(light=50, super_=5) == (100, 100)
    loadout.set_energy("super", 0)
    assert loadout.gain(light=5, super_=10) == (100, 10)
    assert character["super_energy"] == 10
    assert [event[0] for event in loadout.regeneration_events()][0] == "New Turn"
