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
