# Mythic TTRPG Data Schema

This document is the source-of-truth contract for JSON data in `data/`. The repository contains rule documents, lookup tables, catalogs, character-creation profiles, and polymorphic records; they do not share one single record shape. Every file follows the common document rules below and one family contract.

## Common Rules

- Files are UTF-8 JSON documents, formatted with two-space indentation.
- The root is an object. Its top-level keys identify the document type.
- Property names use `snake_case`; game-facing names and characteristic codes preserve their source spelling.
- Unknown fields are allowed in rule records so new source material can be added without destroying data.
- `null` means the source explicitly has no value. An omitted field means the field is not applicable or is not supplied.
- A value may be a number, string, boolean, object, array, or `null` when the source uses mixed representations. Rules that need arithmetic should normalize numeric strings at runtime.
- Repeated records use objects with a required `name` where the source provides a name. Unnamed table rows may use the source's table fields directly.
- Optional source citations use `citation`, `reference_page`, or `source`.

## Shared Definitions

```text
CharacteristicCode = STR | TOU | AGI | WFR | WFM | INT | PER | CRG | CHA | LDR
CharacteristicMap = object keyed by CharacteristicCode with number|string|null values
Range = [number|string|null, number|string|null]
NamedRecord = { name: string, ...additional source fields }
Trait = { name: string, effect: string, ...optional fields }
Cost = number|string|object
RuleText = string|number|boolean|object|array|null
```

## Soldier Type

Files: `core/unsc_soldier_types/*.json`, `light_and_sky/character_creation/human_soldier_types/*.json`, and `light_and_sky/character_creation/guardian_classes_subclasses/*.json`.

```json
{
  "name": "string",
  "experience_cost": "number",
  "training": ["string"],
  "upbringing": "string or [string]",
  "base_characteristics": "CharacteristicMap",
  "mythic_characteristics": "CharacteristicMap",
  "advancements": "CharacteristicMap",
  "physical_attributes": {
    "height_cm": "Range",
    "weight_kg": "Range",
    "size": "string"
  },
  "traits": ["Trait"],
  "optional_rules": "object",
  "insurrectionist_rules": "object",
  "special_rules": "object",
  "subclasses": {
    "subclass_name": {
      "characteristic_modifiers": "CharacteristicMap",
      "...additional subclass fields": "RuleText"
    }
  },
  "equipment_sets": { "set_name": ["string"] }
}
```

Each `equipment_sets` pack is an array whose entries are one of: a plain string for gear that has no armory record yet (`"Flashlight"`); a weapon reference `{ "weapon": string, "quantity"?: number, "note"?: string, "label"?: string }`, where `weapon` is the exact `name` of a record in `core/equipment/unsc_weapons.json` or `unsc_grenades_and_explosives.json`, `quantity` defaults to 1, and `label` keeps the book's wording for display; an armor reference `{ "armor": string, "label"?: string }` naming a record in `core/equipment/unsc_armor.json`; or a choice group `{ "label"?: string, "choose_one": [reference, ...] }` where the player picks one option. The first armor a pack yields is saved as `character.armor`; any further armor is carried as an equipment line. A character's pack picks are saved as weapon names, one per choice group, in `selections.equipment.choices`, and the resolved weapons are saved in `character.weapons` as `{ "name", "quantity", "nickname"?, "note"?, "category"? }` objects.

Spartan soldier types list their starting suits in `special_rules.mjolnir_armor.armor_options` as `{ "armor": string, "years": string, "label": string }`, where `armor` names a record in `core/equipment/unsc_armor.json` and `years` is the book's Armor Usage span (shown as guidance, not enforced). An optional `bonus_while_worn` `{ "armor": [string], "characteristics": CharacteristicMap }` adds bonuses while one of the listed suits is worn (Spartan IV: +5 STR, TOU, and AGI in GEN II/III). The character stores the suit in `armor`, the fitted Mjolnir variant in `armor_variant` (`{ "name", "generation", "price" }` or `null`), and the combined suit and soldier-type bonuses in `armor_bonus` (keys `STR`, `mythic_STR`, `TOU`, `AGI`, `mythic_AGI`); these bonuses are not added to base characteristics. The picks are saved in `selections.equipment.starting_armor`. `character.armor_equipped` (default `true` when the character has armor) is toggled on the character sheet; while it is true, the worn armor's `characteristic_bonus` (which may be negative, e.g. an E.O.D BDU's -10 AGI) and any soldier-type `bonus_while_worn` are added to the displayed characteristics and to everything derived from them. Saved characteristics stay the base values.

`physical_attributes`, `insurrectionist_rules`, and `equipment_sets` may be empty objects when the source table does not define them. `special_rules` is intentionally open-ended because soldier types contain named rules with different shapes. `mythic_characteristics` and `advancements` may be empty or partial maps.

## Character Creation

- `upbringing`: `{ "upbringing": [NamedRecord] }`, with `bonuses`, `penalties`, and `environment_available` arrays where supplied.
- `environment`: `{ "environment": [NamedRecord] }`, with `bonuses` and `penalties` arrays.
- In `upbringing` and `environment` records, each `bonuses`/`penalties` entry is either a modifier string that always applies (`"+5 Charisma"`, `"+2 Wounds"`) or a choice group `{ "choose_one": [option, ...] }`, where the player picks one option. An option is a modifier string or an array of modifiers taken together (Laborer: `["+2 Strength", "+1 Toughness"]`). This mirrors the rulebook's "X or Y" wording.
- `lifestyle`: `{ "lifestyle": [{ "name": string, "outcomes": [{ "roll": string, "bonuses": [string], "penalties": [string] }] }] }`.
- `experience_tiers`: `{ "experience_tiers": { "tiers": [record], "luck": number, "credits": number, "notes": string } }`.
- `creation_points`: `{ "creation_points": object }`.
- `languages`: `{ "languages": { "rules": object, "notes": string } }`.
- `weapon_training`, `wounds_formula`, and `outliers`: named rule documents whose nested fields remain source-defined.
- `light_and_sky/character_creation/connections.json`: `{ "connections": { "rules": object, "light": [record], "darkness": [record], "specialized": [record], ... } }`.

## Core Catalogs and Lookup Tables

These documents use a named top-level collection whose value is an array of records, unless noted otherwise:

```text
characteristics, size_categories, low_characteristics, zero_characteristics,
skills, actions, action_subtypes, action_types, equipment_packs, rank_credit_multipliers,
weapon_training, weapon_tags, special_rules, hit_locations, medical_effects,
environmental_effects, wounds, damage, defense, training, terrain, weather, lighting,
ground_type, background_noise, movement_stealth_modifiers, passive_perception, radar,
visr, iff, smartlink, camouflage, active_camouflage, listening, cover, pierce,
scatter, initiative, speed_combat, time, turn_structure, attack_limits, attack_sequence
```

Catalog records may contain `name`, `description`, `effect`, `rules`, `modifiers`, `requirements`, `cost`, `citation`, and additional source fields. Lookup maps use the source's key names and may contain scalar values, arrays, or nested objects.

## Skills and Education

```json
{
  "skills": [{
    "name": "string",
    "difficulty": "string",
    "characteristics": ["string"],
    "type": ["string"],
    "cost": { "trained": "number", "+10": "number", "+20": "number" },
    "description": "string",
    "opposed_by": ["string"],
    "modifiers": [{ "value": "string", "example": "string" }],
    "subsections": [{ "name": "string", "text": "string" }]
  }],
  "difficulty_modifiers": [{ "difficulty": "string", "modifier": "number" }]
}
```

`opposed_by`, `modifiers`, and `subsections` may be omitted when the source has no entries.

```json
{
  "general_education": ["EducationRecord"],
  "street_smarts": ["EducationRecord"]
}
```

An `EducationRecord` contains `name`, `difficulty`, `characteristics_or_skills`, `cost`, and optional `description`.

## Combat, Movement, Actions, and Cyber Warfare

These families use open record documents because the source varies by rule:

- Action records: `name`, `length`, `subtype`, `description`, optional `effects`, and optional `citation`.
- Combat and movement rules: named top-level object containing tables, formulas, modifiers, thresholds, and narrative rule text.
- Melee and ranged combat: named arrays or maps of attacks, stances, ranges, firing modes, weapon tables, and action results.
- Cyber warfare: named arrays/maps of protocols, software, AI, firewalls, upgrades, encryption, hacking, and defenses. `effect` may be text or a structured object.
- Luck: named rule documents for spending, burning, and encounter/medical/narrative outcomes.
- Wounds and medical: named tables for locations, wounds, special damage, medical effects, and environmental effects.

All records in these families may use `citation`, `reference_page`, `requirements`, `modifiers`, `effects`, `outcomes`, `roll`, `threshold`, and `notes` when provided by the source.

## Equipment

- `combat/armor.json`: armor catalog/table document. It may contain armor tables, `armor_subtype`, `armor_variant`, `armor_perks`, and `exotic_armor_perks`.
- `light_and_sky/equipment/armor.json`: armor catalog with timeline, material tables, modules, perks, and variants.
- `light_and_sky/equipment/weapons.json`: grouped weapon arrays such as `scout_rifles`, `pulse_rifles`, and `sidearms`; weapon records contain source-defined combat fields including `rate_of_fire`, `damage`, `bonus_damage`, `pierce`, `range`, `magazine`, `reload`, `tags`, `ammo_type`, and `weapon_type`.
- `core/equipment/unsc_weapons.json`: `{ "unsc_weapons": { group: [WeaponRecord] }, "citation": string }`. Groups are `pistols`, `smgs`, `rifles`, `machine_guns`, `sniper_rifles`, `shotguns`, `energy_weapons`, `chemical_sprayers`, `rocket_launchers`, `missile_launchers`, `grenade_launchers`, `mortar_launchers`, and `melee_weapons`. Vehicle weaponry and turrets are not included.
- `core/equipment/unsc_grenades_and_explosives.json`: `{ "unsc_explosives": { "grenades" | "satchel_charges" | "demolitions" | "landmines": [WeaponRecord] }, "citation": string }`.
- A core `WeaponRecord` uses the same combat field names as Light and Sky weapons: `name`, optional `nickname` (the book's short name), `faction`, `weapon_type`, `weight_kg`, `damage` (dice roll), `bonus_damage` (base damage, without a leading `+`), `pierce`, `price`, `tags` (`I`, `U`, `UD`, `OH`, `TH`, `DW`, `HW`, `PD`, `SD`, `BD`, without brackets), `special_rules` (array of rule names such as `"Blast (8)"`), optional `comes_with` (array), and `description` (the full rule text after the tags). Ranged weapons add `rate_of_fire`, `range`, `magazine`, `magazine_type` (`Magazine`, `Tube`, `Belt`, `Battery`, or `Tank`), `reload`, and `ammunition`. Melee weapons use `reach` instead of `range`; shields add `shield_armor` and `breakpoints`; a weapon with two damage profiles adds `damage_profile` and `alternate_profiles`. Explosives use `range` for the Blast/Kill radii. `--` in the book is stored as `null`; values containing formulas (`"(X)D10"`, `"4 +Full Strength Modifier"`) stay text.
- `core/equipment/unsc_armor.json`: `{ "unsc_armor": { group: [ArmorRecord] }, "citation": string }`. Groups are `pre_war_bdus`, `covenant_war_bdus`, `post_war_bdus`, `police_armor`, `odst_bdus`, `semi_powered_infiltration`, `orcus`, `mjolnir_prototypes`, and `mjolnir`. An `ArmorRecord` has `name` (unique across the file; BDUs that repeat between eras get the era appended, e.g. `"Vacuum (Post-War)"`), `faction`, `armor_type` (`Standard`, `Semi-Powered`, or `Powered`), `weight_kg`, `price` (cR; `null` for Mjolnir, which lists no price), `armor_rating` (`{ "head", "arms", "chest", "legs" }`), `special_rules`, and `description`. Optional fields: `era`, `variant_of` (ODST variants name the standard ODST BDU), `comes_with`, `energy_shields` (`{ "integrity", "delay", "recharge" }`), `characteristic_bonus` (`{ "STR", "mythic_STR", "AGI", "mythic_AGI" }`), `traits` and `spartan_abilities` (arrays of `{ "name", "description" }`), `generation`, `variant_generations`, `size`, and `restrictions`.
- `core/equipment/unsc_armor_variants.json`: `{ "mjolnir_variants": { "gen_i" | "gen_ii" | "gen_iii": [{ "name", "generation", "price", "description" }] } }`. Names are unique within a generation, not across them.
- `core/equipment/unsc_armor_permutations.json`: `{ "armor_permutations": { "universal" | "helmet" | "legs" | "full_body" | "arms" | "chest": [{ "name", "location", "hardpoints", "price", "description", "weight_kg"? }] }, "permutation_hardpoints": object }`.
- Equipment records may use numeric strings for dice, ranges, Pierce, ammunition, and other values because these values can contain formulas or units.

## Light and Sky

- `light_aspect_rules.json`: `{ "light_aspects": { "rules": object } }`.
- `light_aspects.json`: `{ "light_aspects": { "arc": [record], "solar": [record], "void": [record], "terraform": [record], "resurrection": [record], "strand": [record], "stasis": [record] } }`; each record has `name`, `experience_cost`, and `description`.
- `light_ability_rules.json`: `{ "light_abilities": { "rules": object, "supers": { ..., "experience_cost_multiplier": number, "energy_cost_multiplier": number }, "grenade_supers": object, "energy": object, "double_jump": object } }`.
- `light_abilities_and_grenades.json`: `{ "abilities": [record], "grenades": [record] }`; abilities use `connection`, `category`, `experience_cost`, `light_cost`, `description`, and optional `super_description`; grenades also use `pierce` (number or null), `base_damage`, `damage_roll`, `range`, and `special_rules`, plus an optional `second_detonation` object with the same four stat fields for grenades that detonate twice with different stats.
- `light_weapon_abilities.json`: `{ "light_weapon_abilities": { "base_ability": object, "effects": { "connection": [record] } } }`; effect records use `description`, `additional_light_energy`, and optional `cost_modifier`.
- `character_creation/guardian_classes_subclasses/*.json`: soldier profiles with required `subclasses` and class-specific characteristic modifiers.

## Validation and Compatibility

Validation must be performed in two layers:

1. **Document validation:** valid UTF-8 JSON, object root, known top-level document family, and correct primitive/container types for that family.
2. **Game validation:** required rules, allowed characteristic codes, non-negative costs, valid ranges, unique names within a catalog, and references to existing skills, abilities, equipment, and Connections.

The schema is intentionally permissive for rule payloads and polymorphic `effects`; the validator must report unknown fields rather than delete them. Files are named in `snake_case` with standard spelling (for example `encumbrance.json`, `camouflage.json`, `multi_targeting.json`). Run `python tools/validate_all.py` to check both layers; it exits non-zero when any error is found.
