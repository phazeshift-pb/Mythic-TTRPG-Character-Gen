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

## Development

Install dependencies with `pip install PySide6 pytest`, then run the app with
`python main.py`. Data paths resolve from the repository, so commands work from
any folder.

- `python tools/validate_all.py` checks every JSON file, loads both rulesets,
  and cross-checks specialization packs against skills and abilities. It exits
  with status 1 on errors. Add `--verbose` to list data files the creator does
  not load yet.
- `python -m pytest tests` runs the unit tests.
