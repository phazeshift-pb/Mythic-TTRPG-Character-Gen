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


class _Combo:
    def __init__(self, data):
        self.data = data

    def currentData(self):
        return self.data


class _Tile:
    def __init__(self):
        self.checked = True

    def blockSignals(self, _):
        pass

    def setChecked(self, value):
        self.checked = value


@pytest.mark.parametrize("guardian_class, limit", [("warlock", 3), ("titan", 2), ("hunter", 2)])
def test_creator_light_power_limit_counts_the_warlock_power_slot(lns_data, guardian_class, limit):
    from src.ui.creator.light_powers import LightPowersMixin

    creator = LightPowersMixin()
    creator.game_data = lns_data
    creator.guardian_combo = _Combo(guardian_class)
    creator._selected_light_aspects, creator._selected_light_supers = {}, {}
    creator._selected_light_powers = {}
    creator._selected_light_xp_cost = lambda: 0
    creator._light_xp_budget = lambda: 10_000
    creator._update_light_xp_display = lambda: None
    creator.update_light_power_selection = lambda: None
    assert creator._light_power_slot_limit() == limit

    tiles = []
    for number in range(4):
        tile = _Tile()
        creator._select_light_tile(tile, "power", True, ("Light Ability", f"p{number}"), {})
        tiles.append(tile)
    assert len(creator._selected_light_powers) == limit
    assert [tile.checked for tile in tiles] == [True] * limit + [False] * (4 - limit)


@pytest.mark.parametrize(
    "outlier, aspects, abilities, light_max, super_max",
    [
        (None, 1, 2, 100, 100),
        ("Passive", 2, 2, 100, 100),
        ("Focus", 1, 3, 100, 100),
        ("Energize", 1, 2, 125, 100),
        ("Super", 1, 2, 100, 120),
    ],
)
def test_guardian_outliers_apply_their_bonuses(lns_data, outlier, aspects, abilities, light_max, super_max):
    loadout = LightLoadout(titan(outliers=[outlier] if outlier else []), lns_data)
    assert loadout.aspect_slot_count() == aspects
    assert loadout.ability_slot_count() == abilities
    assert loadout.maximum("light") == light_max
    assert loadout.maximum("super") == super_max
    assert loadout.energy("light") == light_max  # a fresh character starts full


def test_outlier_free_slots_stack_with_warlock_and_do_not_use_up_purchases(lns_data):
    character = titan(soldier_type="Warlock Class Soldier Type", outliers=["Passive", "Focus"])
    loadout = LightLoadout(character, lns_data)
    # 2 starting + Warlock + Focus, then 3 purchasable
    assert [slot.unlocked for slot in loadout.slots("ability")] == [True] * 4 + [False] * 3
    # 1 starting + Passive, then 3 purchasable priced 200 / 400 / 800 in order
    aspect_slots = loadout.slots("aspect")
    assert [slot.unlocked for slot in aspect_slots] == [True, True, False, False, False]
    assert [slot.unlock_cost for slot in aspect_slots[2:]] == [200, 400, 800]
    assert "1 free from Outliers" in loadout.shop.find("ability_slot").current
    assert loadout.shop.find("aspect_slot:2").next == "3 Aspect Slots"


def test_creator_outliers_raise_creation_picks(lns_data):
    from types import SimpleNamespace

    from src.ui.creator.light_powers import LightPowersMixin

    creator = LightPowersMixin()
    creator.game_data = lns_data
    creator.guardian_combo = _Combo("warlock")
    assert (creator._light_aspect_slot_limit(), creator._light_power_slot_limit()) == (1, 3)
    creator.generated_character = SimpleNamespace(outliers=["Passive", "Focus"])
    assert (creator._light_aspect_slot_limit(), creator._light_power_slot_limit()) == (2, 4)
