# Mythic TTRPG Character Gen

## Character exports

Choose **Finish and Name Your Character** from the Character Creator home screen
after completing equipment or Light & Sky selections to save an editable JSON
character file in the project-level `characters` folder. The character name is
used as the filename; characters with the same filename require overwrite
confirmation.

Each export has a `format_version` field, a `ruleset`, a `character` object
containing the character's generated data, and a `selections` object containing
the choices made during creation. `selections.initial_setup` varies by ruleset;
`creation_points` records the point option and per-characteristic allocations;
and `outliers`, `specialization_packs`, and `equipment` record later choices.

Choose **Load Character** on the landing screen to open an exported JSON file in
the interactive character sheet. Its **Character** and **Combat & Notes** tabs
follow the printable sheet's identity, characteristics, skills, resources,
equipment, and notes sections. Movement has its own half-width panel, alongside
separate Perceptive Range and Carrying Capacity panels. Wounds, fatigue,
credits, notes, available Luck, and total Luck can be adjusted while the sheet
is open, but these changes are not yet saved back to the character file. Outliers
permanently reduce total Luck without changing available Luck. Fields not
included in the character export are shown as unavailable. Movement speeds are
calculated from Agility, its characteristic modifier, and any Mythic Agility
bonus. Perceptive Range is calculated as Perception × 2, with applicable
outlier bonuses such as Vigil's increased range multiplier. Carry, Lift, and
Push capacities use the encumbrance formulas and include Mythic bonuses,
applicable soldier traits, and Strongman or Strong Back effects. Mythic
Strength, Toughness, and Agility values appear in separate boxes below their
base characteristics.
