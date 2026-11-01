"""To Hit target for an attack (Mythic 7.0 CU1 combat rules).

Pure functions, no Qt. The character sheet's Attack Calculator builds an
AttackOptions from its controls and shows the AttackResult.

Sources (Mythic 7.0 CU1): Combat Actions (Aim, Called Shot, Blind Fire,
Charge, Guarded Attack), Movement Actions, Weapon Wielding, Ranged Combat
(ranges, Perceptive Range, lighting, weather), Firing Types, Size Category,
Attacks and Movement Speeds, thrown weapon Penalties in the Melee Weapons
section, and Abilities. Most values are also in data/ (combat/, ranged_combat/,
melee_combat/, actions/combat_actions.json).
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

# Attack modes
FIRE = "fire"      # shoot the weapon: Warfare Range
MELEE = "melee"    # strike with it (or a Buttstroke): Warfare Melee
THROW = "throw"    # throw it: Warfare Melee

MODE_LABELS = {
    FIRE: "Fire (Warfare Range)",
    MELEE: "Melee strike (Warfare Melee)",
    THROW: "Throw (Warfare Melee)",
}
MODE_CHARACTERISTIC = {FIRE: "WFR", MELEE: "WFM", THROW: "WFM"}

UNARMED = "Unarmed"

# ---------------------------------------------------------
# Rule values
# ---------------------------------------------------------
FIRE_MODE_BONUS = {"semi-auto": 10, "burst": 10}  # Firing Types
NOT_FIRE_MODES = {"charge", "drawback"}  # timing rules, not a way to fire

RANGED_POINT_BLANK = 20  # within 3 m, target hasn't moved
MELEE_POINT_BLANK = 10   # within 1 m
CLOSE_RANGE = 5
LONG_RANGE = -40
EXTREME_RANGE = -80

ONE_HANDED = {"DW": 0, "OH": -10, "TH": -20, "HW": -40}  # Using Weapons One-Handed
DUAL_WIELD_EXTRA = -10
MYTHIC_WIELD_REDUCTION = 5
MYTHIC_WIELD_MINIMUM = 10
UNBRACED_HEAVY = -20

AIM = {"none": ("No Aim", 0), "half": ("Half Aim", 5), "full": ("Full Aim", 10)}
LASER = 5

# key: (label, ranged/throw penalty, melee modifier)
MOVEMENT = {
    "none": ("Not moving", 0, 0),
    "half": ("Half Move", -20, -20),
    "full": ("Full Move", -20, -20),
    "charge": ("Charge", -30, 10),  # a Charge ends in a +10 Charge Attack
    "run": ("Run", -40, -40),
}
MOBILE_FIRE_REDUCTION = 10

CALLED_SHOTS = {
    "location": ("Body location", -30),
    "sublocation": ("Sublocation", -60),
    "weapon": ("Weapon (standard)", -40),
    "large_weapon": ("Weapon (Large or Heavy)", -20),
}

LIGHTING = {
    "normal": ("Normal light", 0),
    "bright": ("Bright", -20),
    "low": ("Low-Light", -20),
    "blinding": ("Blinding", -50),
    "darkness": ("Darkness", -50),
}
WEATHER = {
    "clear": ("Clear", 0),
    "light": ("Light fog, smoke or rain", -5),
    "moderate": ("Moderate fog, smoke or rain", -10),
    "heavy": ("Heavy rain or debris", -20),
    "severe": ("Heavy fog, downpour or tremors", -30),
}
PERCEPTIVE = {
    "within": ("Within Perceptive Range", 0),
    "double": ("Up to 2x Perceptive Range", -20),
    "triple": ("Up to 3x Perceptive Range", -60),
}
# key: (label, ranged modifier, melee modifier)
TARGET_STANCE = {
    "standing": ("Standing", 0, 0),
    "crouched": ("Crouched", -5, 5),
    "prone": ("Prone", -10, 10),
}
# Size Category: +10 To Hit per category above Immense
TARGET_SIZE = {
    "normal": ("Immense or smaller", 0),
    "massive": ("Massive", 10),
    "great": ("Great", 20),
    "monumental": ("Monumental", 30),
    "colossal": ("Colossal", 40),
    "vast": ("Vast", 50),
}
SPEED = {
    "none": ("Under 100 MpT difference", 0),
    "100": ("100 MpT difference", -10),
    "200": ("200 MpT difference", -20),
    "300": ("300 MpT difference", -40),
    "400": ("400+ MpT difference", -80),
}
SPEED_HALF_TYPES = ("sniper", "energy", "railgun", "coil")
BLIND_FIRE = {
    "none": ("Target visible", 0),
    "blind": ("Blind Fire", -60),
    "smartlink": ("Blind Fire with Smartlink", -30),
}

# key: (label, value, modes it applies to)
SITUATIONAL = {
    "outnumbering": ("Allies outnumber the target", 10, {MELEE}),
    "into_melee": ("Shooting into melee", -20, {FIRE, THROW}),
    "switched_target": ("Switched targets this Round", -10, {FIRE, MELEE, THROW}),
    "guarded_attack": ("Guarded Attack action", -10, {FIRE, MELEE, THROW}),
    "faction": ("Unfamiliar faction technology", -20, {FIRE, MELEE, THROW}),
    "untrained": ("No Weapon Training for this weapon", -20, {FIRE, MELEE, THROW}),
}

# Weapon Training categories by armory weapon_type (data/character_creation/weapon_training.json)
TRAINING_ALIASES = {
    "light machine gun": "LMG",
    "heavy machine gun": "HMG",
    "machine gun": "MG",
    "mortar launcher": "Mortar Cannon",
}

# ---------------------------------------------------------
# Abilities
# ---------------------------------------------------------
# name: (what it does, modes it is relevant to, on by default)
ABILITIES = {
    "Hand-To-Hand Basic": ("+5 To Hit with Melee Attacks", {MELEE}, True),
    "Modern Army Combative": ("+5 To Hit with Melee Attacks", {MELEE}, True),
    "Guarded": ("+10 To Hit attacking with a Physical Shield", {MELEE}, True),
    "Steady Aim": ("+10 To Hit with Aim Actions (not as a Reaction)", {FIRE, MELEE, THROW}, True),
    "Clear Target": ("Halves Called Shot Penalty (ranged)", {FIRE, THROW}, True),
    "Precision Strike": ("Halves Called Shot Penalty (melee)", {MELEE}, True),
    "Mobile Fire": ("Moving Penalty reduced by 10 when firing", {FIRE}, True),
    "Akimbo": ("Halves Dual Wielding Penalty", {FIRE, MELEE}, True),
    "Marksman": ("Half Long and Extreme Range Penalties with Sniper Optics", {FIRE}, True),
    "Faster Than Reloading": ("No -30 Penalty when throwing a Firearm", {THROW}, True),
    "Aggressive Advance": ("First shot of a Charge has no Penalty", {FIRE}, True),
    "Blind Fight": ("Half eyesight Penalties (lighting, weather)", {FIRE, MELEE, THROW}, True),
    "Evasive Maneuvers": ("Declared this Turn: -20 To Hit", {FIRE, MELEE, THROW}, False),
    "Strafing Run": ("Strafing while moving: -10 To Hit", {FIRE, MELEE, THROW}, False),
}


# ---------------------------------------------------------
# Weapon profile
# ---------------------------------------------------------
@dataclass(frozen=True)
class FireMode:
    name: str
    value: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.value})" if self.value else self.name

    @property
    def bonus(self) -> int:
        return FIRE_MODE_BONUS.get(_fire_mode_key(self.name), 0)


@dataclass(frozen=True)
class WeaponProfile:
    name: str
    weapon_type: str = ""
    tags: tuple = ()
    rate_of_fire: str = ""
    range_text: str = ""
    kind: str = "firearm"  # firearm, melee, grenade, unarmed

    @property
    def wield_tag(self) -> Optional[str]:
        """The heaviest wielding tag: armory weapons often list both [TH] and [HW]."""
        return next((tag for tag in ("HW", "TH", "OH", "DW") if tag in self.tags), None)

    @property
    def modes(self) -> list:
        if self.kind == "grenade":
            return [THROW]
        if self.kind in ("melee", "unarmed"):
            return [MELEE] if self.kind == "unarmed" else [MELEE, THROW]
        return [FIRE, MELEE, THROW]

    @property
    def default_mode(self) -> str:
        return self.modes[0]

    @property
    def fire_modes(self) -> list:
        return parse_fire_modes(self.rate_of_fire)

    @property
    def ranges(self) -> Optional[tuple]:
        return parse_range(self.range_text)


def _fire_mode_key(name: str) -> str:
    key = re.sub(r"[\s_]+", "-", name.strip().lower())
    return "semi-auto" if key.startswith("semi") else key


def parse_fire_modes(text: Any) -> list:
    """'Semi-Auto (2), Auto (6), Burst (2)' -> FireModes; Charge/Drawback are left out."""
    found = re.findall(r"([A-Za-z][A-Za-z\- ]*?)\s*\(([^)]*)\)", str(text or ""))
    modes = []
    for name, value in found:
        name = re.sub(r"^(with|and)\s+", "", name.strip(), flags=re.IGNORECASE)
        if _fire_mode_key(name) not in NOT_FIRE_MODES:
            modes.append(FireMode(name, value.strip()))
    if not modes and str(text or "").strip():
        modes.append(FireMode(str(text).strip(), ""))
    return modes


def parse_range(text: Any) -> Optional[tuple]:
    """'20m-100m' -> (20, 100): Close under the first number, Long/Extreme past the second."""
    cleaned = re.sub(r"(?<=\d),(?=\d{3})", "", str(text or ""))
    match = re.search(r"(\d+(?:\.\d+)?)\s*m?\s*[-–]\s*(\d+(?:\.\d+)?)\s*m", cleaned, re.IGNORECASE)
    if not match:
        return None
    low, high = (float(group) for group in match.groups())
    return (int(low) if low.is_integer() else low, int(high) if high.is_integer() else high)


def weapon_profile(weapon: Any, armory: Optional[dict] = None) -> WeaponProfile:
    """Profile for a character's weapon entry (armory weapon, loot weapon or name)."""
    if weapon == UNARMED:
        return WeaponProfile(UNARMED, "Unarmed", ("DW",), kind="unarmed")
    entry = weapon if isinstance(weapon, dict) else {"name": str(weapon)}
    name = str(entry.get("name") or "Unknown weapon")
    record = dict((armory or {}).get(name) or {})
    if isinstance(entry.get("loot"), dict):
        record = {**entry["loot"], **record}
    weapon_type = str(record.get("weapon_type") or "")
    group = str(record.get("_group") or "")
    family = str(record.get("_family") or "")
    if weapon_type.lower() == "grenade" or group == "grenades" or family == "unsc_explosives":
        kind = "grenade"
    elif group == "melee_weapons" or ("reach" in record and not record.get("rate_of_fire")):
        kind = "melee"
    else:
        kind = "firearm"
    return WeaponProfile(
        name=name,
        weapon_type=weapon_type,
        tags=tuple(str(tag) for tag in record.get("tags") or ()),
        rate_of_fire=str(record.get("rate_of_fire") or ""),
        range_text=str(record.get("range") or ""),
        kind=kind,
    )


def range_bands(profile: WeaponProfile, mode: str) -> list:
    """[(key, label, modifier)] range choices for this weapon and attack mode."""
    if mode == MELEE:
        return [("normal", "In Melee reach", 0), ("point_blank", "Point Blank (within 1 m)", MELEE_POINT_BLANK)]
    if mode == THROW:
        return [("normal", "Within throwing distance", 0)]
    bands = [("point_blank", "Point Blank (within 3 m)", RANGED_POINT_BLANK)]
    ranges = profile.ranges
    if ranges is None:
        return bands + [("optimal", "In range", 0)]
    low, high = ranges
    return bands + [
        ("close", f"Close (under {low:g} m)", CLOSE_RANGE),
        ("optimal", f"Optimal ({low:g}-{high:g} m)", 0),
        ("long", f"Long ({high:g}-{high * 2:g} m)", LONG_RANGE),
        ("extreme", f"Extreme ({high * 2:g}-{high * 3:g} m)", EXTREME_RANGE),
    ]


def default_range(profile: WeaponProfile, mode: str) -> str:
    keys = [key for key, _, _ in range_bands(profile, mode)]
    return "optimal" if "optimal" in keys else keys[0]


def training_category(profile: WeaponProfile, training_doc: Optional[dict]) -> Optional[str]:
    """Name of the Weapon Training that covers this weapon, or None if unknown."""
    records = ((training_doc or {}).get("weapon_training") or {}).get("training") or []
    wanted = TRAINING_ALIASES.get(profile.weapon_type.lower(), profile.weapon_type).lower()
    for record in records:
        if any(str(weapon).lower() == wanted for weapon in record.get("weapons", [])):
            return record.get("name")
    if profile.kind == "melee":
        for record in records:
            if any("non-knife melee" in str(weapon).lower() for weapon in record.get("weapons", [])):
                return record.get("name")
    return None


def is_untrained(profile: WeaponProfile, owned_training: Any, training_doc: Optional[dict]) -> Optional[bool]:
    """True/False when the Weapon Training rules cover the weapon, None when unknown."""
    if profile.kind == "unarmed":
        return False
    category = training_category(profile, training_doc)
    if category is None:
        return None
    return category not in set(owned_training or ())


def thrown_penalty(profile: WeaponProfile, abilities: set) -> tuple:
    """(Penalty, explanation) for throwing this weapon."""
    weapon_type = profile.weapon_type.lower()
    tag = profile.wield_tag
    if profile.kind == "grenade":
        return 0, ""
    if profile.kind == "firearm":
        if "Faster Than Reloading" in abilities:
            return 0, "Thrown Firearm (Faster Than Reloading)"
        return -30, "Thrown Firearm"
    if "knife" in weapon_type or "dagger" in weapon_type:
        return ({"DW": -5}.get(tag, -10), "Thrown knife or dagger")
    if "fist" in weapon_type:
        return -10, "Thrown Fist Weapon"
    penalty = {"DW": -10, "OH": -20, "TH": -30, "HW": -40}.get(tag, -20)
    if "spear" in weapon_type:
        return penalty // 2, "Thrown Spear"
    return penalty, "Thrown melee weapon"


# ---------------------------------------------------------
# Options and result
# ---------------------------------------------------------
@dataclass
class AttackOptions:
    characteristic: int
    mythic_strength: int = 0
    mode: str = FIRE
    fire_mode: Optional[FireMode] = None
    range_band: str = "optimal"
    wielding: str = "two"  # two, one, dual
    braced: bool = False
    aim: str = "none"
    laser: bool = False
    movement: str = "none"
    first_charge_shot: bool = True
    called_shot: bool = False
    called_target: str = "location"
    lighting: str = "normal"
    weather: str = "clear"
    perceptive: str = "within"
    target_stance: str = "standing"
    target_size: str = "normal"
    speed: str = "none"
    blind_fire: str = "none"
    situational: set = field(default_factory=set)
    abilities: set = field(default_factory=set)  # abilities switched on
    custom: int = 0


@dataclass
class AttackResult:
    characteristic_name: str
    characteristic: int
    modifiers: list  # [(label, value)]
    notes: list

    @property
    def total(self) -> int:
        return self.characteristic + sum(value for _, value in self.modifiers)

    @property
    def total_modifier(self) -> int:
        return sum(value for _, value in self.modifiers)


def relevant_abilities(owned: Any, profile: WeaponProfile, mode: str) -> list:
    """[(name, effect, on by default)] for abilities the character has that touch this attack."""
    owned = {str(name) for name in owned or ()}
    result = []
    for name, (effect, modes, default) in ABILITIES.items():
        if name not in owned or mode not in modes:
            continue
        if name == "Guarded" and "shield" not in profile.weapon_type.lower():
            continue
        if name == "Marksman" and "sniper" not in profile.weapon_type.lower():
            continue
        if name == "Akimbo" and profile.kind == "unarmed":
            continue
        result.append((name, effect, default))
    return result


def _halve(value: int) -> int:
    return int(value / 2)  # toward zero: -45 -> -22


def attack_target(profile: WeaponProfile, options: AttackOptions) -> AttackResult:
    mode = options.mode if options.mode in profile.modes else profile.default_mode
    on = set(options.abilities)
    modifiers = []
    notes = []

    def add(label, value):
        if value:
            modifiers.append((label, int(value)))

    # Fire rate
    if mode == FIRE and options.fire_mode is not None:
        add(f"{options.fire_mode.name} fire", options.fire_mode.bonus)

    # Range
    bands = {key: (label, value) for key, label, value in range_bands(profile, mode)}
    band_label, band_value = bands.get(options.range_band, (None, 0))
    if options.range_band in ("long", "extreme") and "Marksman" in on:
        band_value = _halve(band_value)
        band_label += " (Marksman)"
    if band_label:
        add(band_label + " range" if mode == FIRE else band_label, band_value)
    if options.range_band == "point_blank":
        notes.append("Point Blank is lost if the target moved since your last Turn.")

    # Thrown weapon
    if mode == THROW:
        penalty, label = thrown_penalty(profile, on)
        add(label, penalty)

    # Wielding
    tag = profile.wield_tag
    if mode in (FIRE, MELEE) and tag and options.wielding in ("one", "dual"):
        penalty = -ONE_HANDED[tag]
        if options.wielding == "dual":
            penalty += -DUAL_WIELD_EXTRA
        exempt = mode == MELEE and profile.kind in ("melee", "unarmed") and tag in ("DW", "OH")
        if penalty and options.mythic_strength > 0:
            floor = 0 if exempt else MYTHIC_WIELD_MINIMUM
            penalty = max(min(penalty, floor), penalty - MYTHIC_WIELD_REDUCTION * options.mythic_strength)
        label = "Dual Wielding" if options.wielding == "dual" else "One-handed"
        if options.braced and tag == "HW":
            penalty = _halve(penalty)
            label += " (Braced)"
        if options.wielding == "dual" and "Akimbo" in on and (tag != "HW" or options.braced):
            penalty = _halve(penalty)
            label += " (Akimbo)"
        add(f"{label} [{tag}]", -penalty)
    if mode == FIRE and tag == "HW" and not options.braced:
        add("Heavy Weapon not Braced", UNBRACED_HEAVY)
        notes.append("Unbraced [HW]: make a Strength Test after each To Hit Test or drop the weapon.")

    # Aim / laser
    blind = BLIND_FIRE.get(options.blind_fire, BLIND_FIRE["none"])
    aim_allowed = options.blind_fire != "blind" or mode != FIRE
    aim_label, aim_value = AIM.get(options.aim, AIM["none"])
    if aim_value and aim_allowed:
        add(aim_label, aim_value)
        if "Steady Aim" in on:
            add("Steady Aim", 10)
        notes.append("Half Aim helps your first attack; Full Aim your first two.")
    elif aim_value:
        notes.append("Blind Fire gets no Aim bonus without a Smartlink.")
    if mode == FIRE and options.laser:
        if aim_value:
            notes.append("Targeting laser doesn't stack with Aim.")
        elif options.blind_fire == "blind":
            notes.append("Blind Fire gets no laser bonus without a Smartlink.")
        else:
            add("Targeting laser", LASER)

    # Movement
    move_label, ranged_move, melee_move = MOVEMENT.get(options.movement, MOVEMENT["none"])
    move_value = melee_move if mode == MELEE else ranged_move
    if mode == FIRE and options.movement == "charge" and "Aggressive Advance" in on and options.first_charge_shot and tag != "HW":
        move_value = 0
        move_label += " (Aggressive Advance, first shot)"
    if mode == FIRE and move_value < 0 and "Mobile Fire" in on:
        move_value = min(0, move_value + MOBILE_FIRE_REDUCTION)
        move_label += " (Mobile Fire)"
    add("Charge Attack" if mode == MELEE and options.movement == "charge" else f"Attacking while {move_label}", move_value)

    # Called shot
    if options.called_shot:
        called_label, called_value = CALLED_SHOTS.get(options.called_target, CALLED_SHOTS["location"])
        halver = "Precision Strike" if mode == MELEE else "Clear Target"
        if halver in on:
            called_value = _halve(called_value)
            called_label += f" ({halver})"
        add(f"Called Shot: {called_label}", called_value)
        notes.append("A missed Called Shot still hits (random location) if it would have hit with 2 Degrees of Success.")

    # Conditions
    eyesight = 0.5 if "Blind Fight" in on else 1
    light_label, light_value = LIGHTING.get(options.lighting, LIGHTING["normal"])
    add(f"Lighting: {light_label}", int(light_value * eyesight))
    weather_label, weather_value = WEATHER.get(options.weather, WEATHER["clear"])
    if weather_value and mode == MELEE:
        weather_value = min(-5, _halve(weather_value))
    add(f"Weather: {weather_label}", int(weather_value * eyesight))
    if mode != MELEE:
        add(PERCEPTIVE.get(options.perceptive, PERCEPTIVE["within"])[0], PERCEPTIVE.get(options.perceptive, PERCEPTIVE["within"])[1])
        if options.perceptive != "within" and aim_value:
            notes.append("Aim Actions can't be taken beyond Perceptive Range.")
    stance_label, stance_ranged, stance_melee = TARGET_STANCE.get(options.target_stance, TARGET_STANCE["standing"])
    add(f"Target {stance_label}", stance_melee if mode == MELEE else stance_ranged)
    size_label, size_value = TARGET_SIZE.get(options.target_size, TARGET_SIZE["normal"])
    add(f"Target size: {size_label}", size_value)
    speed_label, speed_value = SPEED.get(options.speed, SPEED["none"])
    if speed_value and mode == FIRE and any(word in profile.weapon_type.lower() for word in SPEED_HALF_TYPES):
        speed_value = _halve(speed_value)
        speed_label += " (halved for this weapon)"
    add(f"Speed: {speed_label}", speed_value)
    if mode == FIRE:
        add(blind[0], blind[1])

    for key in sorted(options.situational):
        label, value, modes = SITUATIONAL.get(key, (None, 0, ()))
        if label and mode in modes:
            add(label, value)

    # Situational abilities
    if "Evasive Maneuvers" in on:
        add("Evasive Maneuvers", -20)
    if "Strafing Run" in on and options.movement != "none":
        add("Strafing Run", -10)

    # Flat ability bonuses
    if mode == MELEE:
        if "Hand-To-Hand Basic" in on:
            add("Hand-To-Hand Basic", 5)
        if "Modern Army Combative" in on:
            add("Modern Army Combative", 5)
        if "Guarded" in on and "shield" in profile.weapon_type.lower():
            add("Guarded (Physical Shield)", 10)

    add("Other / GM modifier", options.custom)
    return AttackResult(MODE_CHARACTERISTIC[mode], int(options.characteristic), modifiers, notes)
