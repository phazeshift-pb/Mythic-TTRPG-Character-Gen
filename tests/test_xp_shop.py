"""XP Shop rules (src/models/xp_shop.py)."""
from dataclasses import asdict

import pytest

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.xp_shop import PurchaseError, XpShop


@pytest.fixture(scope="module")
def core_data():
    return DataLoader().load_all()


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


def core_character(core_data, soldier="marine", xp=20000):
    character = CharacterGenerator(core_data).generate(
        "t", soldier, starting_experience=xp, auto_assign_skills=False
    )
    data = asdict(character)
    data.pop("debug_log")
    return data


def guardian(lns_data, guardian_class="titan", subclass=None, connection="Arc", xp=30000):
    record = lns_data.get("soldier_type", guardian_class)
    subclass = subclass or next(iter(record["subclasses"]))
    character = CharacterGenerator(lns_data, use_light_and_sky=True).generate(
        "g",
        guardian_class,
        subclass=subclass,
        human_soldier_type="human_awoken",
        guardian_class=guardian_class,
        connection=connection,
        starting_experience=xp,
        auto_assign_skills=False,
    )
    data = asdict(character)
    data.pop("debug_log")
    return data


def item(shop, key):
    found = shop.find(key)
    assert found is not None, key
    return found


def test_core_character_gets_no_light_and_sky_tabs(core_data):
    shop = XpShop(core_character(core_data), core_data, "Core")
    categories = shop.categories()
    assert "Characteristics" in categories and "Skills" in categories
    assert not {"Connections", "Light Aspects", "Supers"} & set(categories)
    assert not any(entry.source == "Light & Sky" for entry in shop.all_items())


def test_light_and_sky_character_gets_core_and_light_tabs(lns_data):
    shop = XpShop(guardian(lns_data), lns_data, "Light & Sky")
    categories = shop.categories()
    for category in ("Characteristics", "Abilities", "Educations", "Connections", "Supers"):
        assert category in categories


def test_characteristic_advancement_starts_after_soldier_type_tiers(core_data):
    character = core_character(core_data)  # Marine: +5 Simple STR, +10 Rookie WFR
    shop = XpShop(character, core_data, "Core")
    strength = item(shop, "characteristic:STR")
    assert strength.cost == 400  # Simple is free, Rookie is next
    warfare_range = item(shop, "characteristic:WFR")
    assert warfare_range.cost == 800  # Intermediate
    toughness = item(shop, "characteristic:TOU")
    assert toughness.cost == 200

    before = character["characteristics"]["STR"]
    xp_before = character["experience"]
    shop.buy(strength)
    assert character["characteristics"]["STR"] == before + 5
    assert character["characteristic_advancements"]["STR"] == 1
    assert character["experience"] == xp_before - 400
    assert character["xp_purchases"][-1]["cost"] == 400
    assert item(shop, "characteristic:STR").cost == 800


def test_characteristic_maxes_after_five_tiers(core_data):
    character = core_character(core_data, xp=60000)
    shop = XpShop(character, core_data, "Core")
    for _ in range(5):
        shop.buy(item(shop, "characteristic:TOU"))
    assert item(shop, "characteristic:TOU").blocked


def test_toughness_advancement_raises_current_wounds(core_data):
    character = core_character(core_data)
    character["characteristics"]["TOU"] = 49
    shop = XpShop(character, core_data, "Core")
    wounds = character["wounds"]
    shop.buy(item(shop, "characteristic:TOU"))  # 49 -> 54: modifier 4 -> 5
    assert character["wounds"] == wounds + 2


def test_skill_trained_then_upgrades(core_data):
    character = core_character(core_data)
    shop = XpShop(character, core_data, "Core")
    technology = item(shop, "skill:Technology")
    assert (technology.cost, technology.next) == (300, "Trained")
    shop.buy(technology)
    assert character["skills"]["Technology"] == 0
    shop.buy(item(shop, "skill:Technology"))
    shop.buy(item(shop, "skill:Technology"))
    assert character["skills"]["Technology"] == 20
    assert item(shop, "skill:Technology").blocked


def test_not_enough_xp_is_refused(core_data):
    character = core_character(core_data, xp=1800)  # Marine costs 1,800
    shop = XpShop(character, core_data, "Core")
    luck = item(shop, "luck")
    allowed, reason = shop.can_buy(luck)
    assert not allowed and "XP" in reason
    with pytest.raises(PurchaseError):
        shop.buy(luck)


@pytest.mark.parametrize(
    "prerequisite, expected",
    [
        ("Strength: 30", True),
        ("Strength: 90", False),
        ("Agility or Intellect: 40", True),
        ("Charisma: 90 or Leadership: 40", True),
        ("Medication: +10 Skill", False),
        ("Pilot (Air): +10 Skill", True),
        ("Disarm Ability", False),
        ("Luck: 1", None),
        ("Berserker or Adrenaline Rush Trait", None),
        ("Strength: 30; Disarm Ability", False),
    ],
)
def test_ability_prerequisites(core_data, prerequisite, expected):
    character = core_character(core_data)
    character["characteristics"].update({"STR": 40, "INT": 45, "CHA": 20, "LDR": 40})
    character["skills"] = {"Pilot": 10}
    character["abilities"] = []
    shop = XpShop(character, core_data, "Core")
    assert shop.prerequisite_status(prerequisite)[0] is expected


def test_ability_purchase_and_block(core_data):
    character = core_character(core_data)
    character["characteristics"]["STR"] = 30
    shop = XpShop(character, core_data, "Core")
    assert item(shop, "ability:Action Figure Hands").blocked  # Strength: 50
    always_ready = item(shop, "ability:Always Ready")
    character["characteristics"]["PER"] = 40
    shop.buy(item(shop, "ability:Always Ready"))
    assert "Always Ready" in character["abilities"]
    assert item(shop, "ability:Always Ready").blocked == "Already owned"
    assert always_ready.cost == 500


def test_educations_limit_choice_and_restricted(core_data):
    character = core_character(core_data)
    character["characteristics"]["INT"] = 25  # modifier 2 -> 4 Educations
    shop = XpShop(character, core_data, "Core")
    assert shop.education_limit() == 4

    culture = item(shop, "education:Faction Culture:+5")
    assert culture.prompt == "text"
    with pytest.raises(PurchaseError):
        shop.buy(culture, choice="")
    shop.buy(culture, choice="UNSC")
    assert character["educations"]["Faction Culture (UNSC)"] == 5
    shop.buy(item(shop, "education:Faction Culture (UNSC):+10"))
    assert character["educations"]["Faction Culture (UNSC)"] == 10

    flood = item(shop, "education:Flood Biology:+5")
    assert flood.needs_gm and flood.prompt == "options"
    assert not shop.can_buy(flood)[0]
    xp = character["experience"]
    shop.buy(flood, gm_override=True, choice="restricted")
    assert character["experience"] == xp - 600  # 3 x 200
    assert character["educations"]["Flood Biology"] == 5

    shop.buy(item(shop, "education:Agriculture:+5"))
    shop.buy(item(shop, "education:Bartering:+5"))
    assert item(shop, "education:Brewing:+5").blocked


def test_training_languages_luck_and_wounds(core_data):
    character = core_character(core_data, xp=40000)
    character["characteristics"]["INT"] = 30  # 3 languages total
    shop = XpShop(character, core_data, "Core")
    assert item(shop, "weapon_training:Basic").blocked  # Marine has Basic, Infantry
    shop.buy(item(shop, "weapon_training:Heavy"))
    assert "Heavy" in character["weapon_training"]
    assert item(shop, "faction_training:UNSC").blocked
    assert item(shop, "faction_training:Forerunner").needs_gm
    shop.buy(item(shop, "faction_training:Covenant"))

    shop.buy(item(shop, "language:new"), choice="Sangheili")
    with pytest.raises(PurchaseError):
        shop.buy(item(shop, "language:new"), choice="sangheili")
    shop.buy(item(shop, "language:new"), choice="Latin")
    assert item(shop, "language:new").blocked

    luck = character["luck_total"]
    shop.buy(item(shop, "luck"))
    assert character["luck_total"] == luck + 1
    character["luck_total"] = 13
    assert item(shop, "luck").blocked

    assert item(shop, "wound_upgrade:Copper").blocked
    wounds_modifier = character["wounds_modifier"]
    shop.buy(item(shop, "wound_upgrade:Iron"))
    assert character["wound_upgrades"] == 1
    assert character["wounds_modifier"] == wounds_modifier + 10
    assert not item(shop, "wound_upgrade:Copper").blocked


def test_orion_augmentation_for_marines_only(core_data):
    marine = core_character(core_data)
    shop = XpShop(marine, core_data, "Core")
    assert "Soldier Type" in shop.categories()
    orion = item(shop, "soldier_upgrade:ORION Augmentation")
    strength = marine["characteristics"]["STR"]
    shop.buy(orion, gm_override=True)
    assert marine["characteristics"]["STR"] == strength + 10
    assert marine["mythic_characteristics"]["TOU"] == "+3"
    assert item(shop, "soldier_upgrade:ORION Augmentation").blocked

    spartan = core_character(core_data, "spartan_ii", xp=40000)
    assert "Soldier Type" not in XpShop(spartan, core_data, "Core").categories()


def test_connections_need_earned_xp_and_light_plus_darkness(lns_data):
    character = guardian(lns_data)
    shop = XpShop(character, lns_data, "Light & Sky")
    assert "earned" in item(shop, "connection:Solar").blocked
    character["starting_experience"] += 2000
    character["experience"] += 2000
    shop = XpShop(character, lns_data, "Light & Sky")
    assert "Light and a Darkness" in item(shop, "connection:Prismatic").blocked
    solar = item(shop, "connection:Solar")
    assert solar.cost == 1000
    shop.buy(solar)
    assert item(shop, "connection:Stasis").cost == 2000
    shop.buy(item(shop, "connection:Stasis"))
    prismatic = item(shop, "connection:Prismatic")
    assert prismatic.needs_gm and not prismatic.blocked


def test_aspect_double_cost_and_prismatic_refund(lns_data):
    character = guardian(lns_data, xp=40000)
    character["starting_experience"] += 10000
    character["experience"] += 10000
    shop = XpShop(character, lns_data, "Light & Sky")
    arc_aspect = next(entry for entry in shop.items("Light Aspects") if entry.next == "Arc")
    void_aspect = next(entry for entry in shop.items("Light Aspects") if entry.next == "Void")
    assert void_aspect.payload["surcharge"] == void_aspect.cost // 2
    assert arc_aspect.payload["surcharge"] == 0
    shop.buy(void_aspect)
    surcharge = void_aspect.payload["surcharge"]

    shop.buy(item(shop, "connection:Stasis"))
    xp_before = character["experience"]
    prismatic = item(shop, "connection:Prismatic")
    entry = shop.buy(prismatic, gm_override=True)
    assert entry["refund"] == surcharge
    assert character["experience"] == xp_before - prismatic.cost + surcharge
    solar_aspect = next(entry for entry in shop.items("Light Aspects") if entry.next == "Solar")
    assert solar_aspect.payload["surcharge"] == 0


def test_light_abilities_follow_connection_and_class(lns_data):
    character = guardian(lns_data, "titan", connection="Arc")
    shop = XpShop(character, lns_data, "Light & Sky")
    abilities = shop.items("Light Abilities")
    hunter_only = next(entry for entry in abilities if entry.name == "Gambler's Dodge")
    assert hunter_only.blocked == "Hunter only"
    solar = next(entry for entry in abilities if "Solar" in entry.requirement)
    assert "Solar" in solar.blocked
    light_weapon = next(entry for entry in abilities if entry.name == "Light Weapon")
    assert not light_weapon.blocked and light_weapon.cost == 500

    super_weapon = next(entry for entry in shop.items("Supers") if entry.name == "Light Weapon")
    assert super_weapon.cost == 750
    shop.buy(super_weapon)
    assert "Light Weapon" in character["supers"]

    grenade = next(entry for entry in abilities if entry.payload["power_type"] == "Light Grenade" and not entry.blocked)
    shop.buy(grenade)
    assert grenade.name in character["light_grenades"]


def test_light_slots(lns_data):
    titan = guardian(lns_data, "titan")
    warlock = guardian(lns_data, "warlock")
    assert XpShop(titan, lns_data, "Light & Sky").ability_slots() == 2
    shop = XpShop(warlock, lns_data, "Light & Sky")
    assert shop.ability_slots() == 3
    for _ in range(3):
        shop.buy(item(shop, "ability_slot"))
    assert shop.ability_slots() == 6
    assert item(shop, "ability_slot").blocked

    assert item(shop, "aspect_slot:3").blocked
    shop.buy(item(shop, "aspect_slot:2"))
    assert shop.aspect_slots() == 2
    assert not item(shop, "aspect_slot:3").blocked


def test_warlock_power_slot_comes_from_soldier_type_data(lns_data):
    from src.models.xp_shop import bonus_light_ability_slots, starting_light_ability_slots

    warlock = lns_data.get("soldier_type", "warlock")
    assert bonus_light_ability_slots(warlock) == 1
    assert bonus_light_ability_slots(lns_data.get("soldier_type", "titan")) == 0
    assert bonus_light_ability_slots(lns_data.get("soldier_type", "hunter")) == 0
    # character creation: 2 starting slots, 3 for a Warlock
    assert starting_light_ability_slots(lns_data, warlock) == 3
    assert starting_light_ability_slots(lns_data, None) == 2
    shop = XpShop(guardian(lns_data, "warlock"), lns_data, "Light & Sky")
    assert shop.class_ability_slots() == 1
    assert "1 free from Warlock" in item(shop, "ability_slot").current
