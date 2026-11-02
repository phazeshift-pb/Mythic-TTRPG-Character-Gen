# Mythic TTRPG Character Gen

## Character exports

Choose **Finish and Name Your Character** from the Character Creator home screen
after completing equipment or Light & Sky selections to save an editable JSON
character file in the project-level `characters` folder. The character name is
used as the filename; characters with the same filename require overwrite
confirmation.

Each export has a `format_version` field, a `ruleset`, a `character` object
containing the character's generated data, and a `selections` object containing
the choices made during creation. `selections.initial_setup` varies by ruleset.
Soldier types with a Skill Training trait prompt for the listed number of skills;
those choices and training levels are recorded there and applied to the
character. `creation_points` records the point option and per-characteristic
allocations, while `outliers`, `specialization_packs`, and `equipment` record
later choices. The selected characteristic for Aptitude or mythic
characteristic for Forte is stored in `selections.outlier_characteristics`.
Upbringings and environments that offer a choice (for example City: "+5 Agility,
Courage, or Perception") open a dialog when selected so you can pick one option
per line. The picks are stored in `selections.initial_setup.background_choices`.
Lifestyles are rolled when the character is generated. If the rolled outcome
offers a choice (Hunter, Weapon Training, and Wise Guy on a 10 ask which Warfare
Characteristic), a dialog shows the roll and asks for it; cancelling stops
generation. Each lifestyle's roll and choices are saved in
`character.lifestyle_results`.

Choose **Load Character** on the landing screen to open an exported JSON file in
the interactive character sheet. Its **Character** and **Combat & Notes** tabs
follow the printable sheet's identity, characteristics, skills, resources,
equipment, and notes sections. Movement has its own half-width panel, alongside
separate Perceptive Range and Carrying Capacity panels. Wounds, fatigue,
credits, experience, equipment, notes, available Luck, and total Luck can be
adjusted while the sheet is open, and **Save** writes them back to the
character file. Outliers
permanently reduce total Luck without changing available Luck. Fields not
included in the character export are shown as unavailable. Movement speeds are
calculated from Agility, its characteristic modifier, and any Mythic Agility
bonus. Perceptive Range is calculated as Perception × 2, with applicable
outlier bonuses such as Vigil's increased range multiplier. Carry, Lift, and
Push capacities use the encumbrance formulas and include Mythic bonuses,
applicable soldier traits, and Strongman or Strong Back effects. Mythic
Strength, Toughness, and Agility values appear in separate boxes below their
base characteristics.

## XP Shop

Press **Spend XP** on a loaded character sheet to open the XP Shop. Pick a
category on the left, then **Buy** a row; each purchase takes its Experience
from the character's current XP. **Undo** reverses the last purchase,
**Cancel** discards the visit, and **Apply to Sheet** returns to the sheet with
the purchases (press **Save** there to write the file). Every purchase is
logged in `character.xp_purchases`.

Core purchases (Mythic 7.0 CU1, Spending Experience p. 51), open to every
character:

- **Characteristics**: +5 Advancements (Simple 200, Rookie 400, Intermediate
  800, Proficient 1,200, Mastery 1,600), up to 5 each, in order. Tiers the
  Soldier Type grants at creation count as owned. Bought tiers are stored in
  `characteristic_advancements`.
- **Skills**: Trained, +10, +20 at each Skill's listed cost.
- **Abilities**: listed cost; characteristic, Skill and Ability prerequisites
  are checked. Luck and Trait prerequisites need GM approval.
- **Educations**: +5 then +10 at the listed cost, up to 2x Intellect Modifier
  Educations. Faction and instrument Educations ask which one. Restricted (*)
  Educations need GM approval and can be bought at 3x cost.
- **Training & Languages**: Weapon Training (Basic 150 ... Ordnance 300),
  Faction Training 300 (Forerunner needs GM approval), Languages 150 each up
  to the Intellect Modifier.
- **Luck & Wounds**: +1 Luck for 1,500 (max 13); Wound Upgrades Iron 500,
  Copper 750, Bronze 1,250, Steel 2,000, Titanium 3,000 (+10 Wounds each,
  in order).
- **Soldier Type**: ORION Augmentation, 4,000 (regular human UNSC types,
  GM approval).

Light & Sky purchases, shown only for Light & Sky characters:

- **Connections**: 2nd 1,000, 3rd 2,000, 4th 4,000, 5th 8,000, once the
  character has earned 2,000 XP since creation. Specialized Connections need
  a Light and a Darkness Connection plus GM approval. Prismatic refunds the
  extra XP paid for off-Connection Light Aspects.
- **Light Slots**: Aspect Slots 2-4 (200, 400, 800); up to 3 extra Light
  Ability Slots at 500 each.
- **Light Aspects**: listed cost, doubled for a Connection the character
  doesn't have.
- **Light Abilities / Grenades** and **Supers** (+50% XP): must match one of
  the character's Connections (or be Universal) and their Guardian Class.

**GM approval** unlocks the purchases marked as needing the GM. Earned XP is
`starting_experience` minus `creation_experience`; older files get
`creation_experience` from `selections.starting_xp` when loaded. Costs and
limits are in `data/xp_shop.json` and the Light & Sky data files; the rules
are in `src/models/xp_shop.py`.

## Light & Sky loot

Light & Sky character sheets have a **Light & Sky Loot** button next to Save.
It opens the random loot generator from the Destiny TTRPG Loot Generator: pick
Weapon or Armor, optionally narrow by ammo type, weapon type, armor material
and rarity, then press **Generate** to roll a loot card. Hover over the card to
read its perk descriptions.

- **Add to Weapons** appends the rolled weapon to the character's weapons. Its
  stats, element, special rules and perks are saved with it
  (`source: "light_and_sky_loot"`, full roll under `loot`).
- **Equip Armor** makes the rolled armor set the character's worn armor (it
  asks before replacing armor already worn). The full roll is saved as
  `armor_loot`, and the set's Agility modifier is saved as `armor_bonus`, so
  the Armor equipped toggle and all worn-armor effects use it.
- **Export Card** saves the loot card as a PNG.

Press **Save** on the sheet afterwards to keep the loot. Rarity odds, exotic
chances, perk counts and rarity colors are in `src/loot/loot_rules.py`; the
tables come from `data/light_and_sky/equipment`, and the element and ammo icons
from `assets/light_and_sky`.

## Light & Sky tab

Light & Sky character sheets get a **Light & Sky** tab after Combat:

- **Energy**: Light Energy and Super Energy (0-100) with bars, a current-value
  box, quick +/- buttons, and regain buttons for the rules' events (New Turn,
  defeating an enemy with weapons or with a Light Ability, assisting an ally).
- **Super**, **Light Ability Slots** and **Aspect Slots**: every possible slot
  is a tile. Bought slots hold one owned power, picked from a drop-down; slots
  not yet bought show **Locked** with their XP cost and a button to the XP
  Shop. Light Grenades fill Light Ability Slots. **Use** / **Cast Super**
  spend the power's energy (Supers cost double, from Super Energy).
- Only slotted Aspects count toward their effects (e.g. movement bonuses).

What is slotted is saved as `light_loadout`
(`{"aspects": [...], "abilities": [...], "super": name, "seen": [...]}`), and
the pools as `light_energy` / `super_energy`. Powers bought since the last
time the sheet was open drop into the first empty slot. The rules are in
`src/models/light_loadout.py`.

## Development

Install dependencies with `pip install PySide6 pytest`, then run the app with
`python main.py`. Data paths resolve from the repository, so commands work from
any folder.

- `python tools/validate_all.py` checks every JSON file, loads both rulesets,
  and cross-checks specialization packs against skills and abilities. It exits
  with status 1 on errors. Add `--verbose` to list data files the creator does
  not load yet.
- `python -m pytest tests` runs the unit tests.
