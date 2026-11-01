# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""The creator's debug report page.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

from src.models.equipment_packs import weapon_summary
from src.models.derived_stats import (
    ROBUST_WOUNDS,
    WOUNDS_BASE,
    WOUNDS_PER_MYTHIC_TOUGHNESS,
    WOUNDS_PER_TOUGHNESS_MODIFIER,
    max_wounds,
    mythic_value,
)


class DebugReportMixin:
    def open_debug_page(self):
        self.debug_page.set_report(self._build_debug_report())
        self.pages.setCurrentWidget(self.debug_page)

    @staticmethod
    def _mythic_value(character, code):
        value = character.mythic_characteristics.get(code, 0)
        if isinstance(value, str):
            return int(value.strip())
        return int(value) if isinstance(value, (int, float)) else 0

    @staticmethod
    def _rule_multiplier(formula, default):
        separator = "*" if "*" in formula else "×" if "×" in formula else None
        if separator is None:
            return default
        return int(formula.rsplit(separator, 1)[1].strip())

    def _outlier_record(self, name):
        document = self.game_data.get("outliers", "outliers") or {}
        return next(
            (
                outlier
                for outlier in document.get("outliers", {}).get("list", [])
                if outlier.get("name") == name
            ),
            {},
        )

    def _build_debug_report(self):
        lines = [
            "CHARACTER GENERATION INPUTS",
            f"Ruleset: {self.selected_mode}",
            f"Starting experience: {self.experience_input.value():,} XP",
            self.experience_tier_label.text(),
        ]

        if self.selected_mode == "Light & Sky":
            lines.extend(
                (
                    f"Human soldier type: {self._selected_option(self.human_combo)}",
                    f"Guardian class: {self._selected_option(self.guardian_combo)}",
                    f"Subclass: {self._selected_option(self.subclass_combo)}",
                    f"Connection: {self._selected_option(self.connection_combo)}",
                )
            )
        else:
            lines.extend(
                (
                    f"Soldier type: {self._selected_option(self.soldier_combo)}",
                    f"Upbringing: {self._selected_option(self.upbringing_combo)}",
                    f"Environment: {self._selected_option(self.environment_combo)}",
                    "Lifestyles: "
                    + ", ".join(
                        self._selected_option(combo)
                        for combo in self.lifestyle_combos
                        if combo.currentText()
                    ),
                )
            )

        lines.extend(
            (
                f"Creation point option: {self.creation_points_combo.currentText() or 'None'}",
                "Creation point allocations: "
                + (
                    ", ".join(
                        f"{code} {amount:+d}"
                        for code, amount in self._creation_allocations.items()
                        if amount
                    )
                    or "None"
                ),
                f"Outliers: {', '.join(self._selected_outlier_names()) or 'None'}",
                f"Specialization packs: {', '.join(self._selected_tile_names(self.specialization_tiles)) or 'None'}",
            )
        )
        if self.selected_mode == "Core":
            selected_equipment = self._selected_tile_names(self.equipment_tiles)
            lines.append(f"Equipment pack: {', '.join(selected_equipment) or 'None'}")
        else:
            selected_aspects = [
                value[0]["name"] for value in self._selected_light_aspects.values()
            ]
            selected_powers = [
                value["name"] for value in self._selected_light_powers.values()
            ]
            selected_supers = [
                value["name"] for value in self._selected_light_supers.values()
            ]
            lines.append(f"Light Aspects: {', '.join(selected_aspects) or 'None'}")
            lines.append(f"Light Abilities / Grenades: {', '.join(selected_powers) or 'None'}")
            lines.append(f"Supers: {', '.join(selected_supers) or 'None'}")

        character = getattr(self, "generated_character", None)
        if character is None:
            lines.extend(
                (
                    "",
                    "CALCULATED OUTPUTS",
                    "Generate a character to calculate derived values.",
                )
            )
            return "\n".join(lines)

        selected_outlier_names = self._selected_outlier_names()
        lines.extend(
            (
                "",
                "GENERATED CHARACTER",
                f"Name: {character.name}",
                f"Soldier type: {character.soldier_type or 'None'}",
                f"Rank: {character.rank or 'None'}",
                f"Background: upbringing={character.upbringing or 'None'}, "
                f"environment={character.environment or 'None'}, "
                f"lifestyle={character.lifestyle or 'None'}",
                f"Starting XP / remaining XP / XP spent: "
                f"{character.starting_experience:,} / {character.experience:,} / "
                f"{character.experience_spent:,}",
                f"Experience tier: {character.experience_tier}",
                "Characteristics: "
                + ", ".join(
                    f"{code} {value}"
                    for code, value in character.characteristics.items()
                ),
                "Mythic characteristics: "
                + (
                    ", ".join(
                        f"{code} {value}"
                        for code, value in character.mythic_characteristics.items()
                    )
                    or "None"
                ),
                f"Skills: {character.skills or 'None'}",
                f"Abilities: {', '.join(character.abilities) or 'None'}",
                f"Outliers applied: {', '.join(character.outliers) or 'None'}",
                f"Specialization packs applied: "
                f"{', '.join(character.specialization_packs) or 'None'}",
                f"Equipment: {', '.join(character.equipment) or 'None'}",
                f"Equipment pack: {character.equipment_pack or 'None'}",
                f"Armor: {character.armor or 'None'}",
                f"Weapons: {', '.join(weapon_summary(w) for w in character.weapons) or 'None'}",
                f"Connections: {', '.join(character.connections) or 'None'}",
                f"Light Aspects: {', '.join(character.light_aspects) or 'None'}",
                f"Light Abilities: {', '.join(character.light_abilities) or 'None'}",
                f"Light Grenades: {', '.join(character.light_grenades) or 'None'}",
                f"Supers: {', '.join(character.supers) or 'None'}",
                f"Wounds / fatigue / credits / Luck available / total: "
                f"{character.wounds} / {character.fatigue} / {character.credits} / "
                f"{character.luck_available} / {character.luck_total}",
                "",
                "CALCULATED OUTPUTS",
            )
        )

        modifier_rules = (
            self.game_data.get("characteristic_modifiers", "characteristic_modifiers")
            or {}
        ).get("modifier_rules", {})
        modifier_formula = modifier_rules.get("below_100", "floor(value / 10)")
        characteristic_modifiers = {
            code: value // 10
            for code, value in character.characteristics.items()
        }

        movement_document = (
            self.game_data.get("movement_speeds", "movement_speeds") or {}
        ).get("movement_speeds", {})
        movement_table = movement_document.get("table", [])
        agility_bonus = self._mythic_value(character, "AGI")
        agility_bonus += sum(
            1
            for aspect in self._selected_light_aspects.values()
            if "Agility Modifier is increased by 1 when figuring Movement Speeds."
            in aspect[0].get("description", "")
        )
        agility_modifier = characteristic_modifiers["AGI"] + agility_bonus
        movement = next(
            (
                row
                for row in movement_table
                if row.get("mod") == agility_modifier
            ),
            None,
        )
        movement_values = (
            ", ".join(
                f"{key.title()} {value} m"
                for key, value in movement.items()
                if key != "mod"
            )
            if movement
            else f"No movement table entry for modifier {agility_modifier}"
        )
        lines.append(
            f"Movement speeds (Agility Modifier {modifier_formula}; "
            f"{characteristic_modifiers['AGI']} + Mythic/Aspect {agility_bonus} = "
            f"{agility_modifier}): {movement_values}"
        )

        wounds_document = (
            self.game_data.get("wounds_formula", "wounds_formula") or {}
        ).get("wounds_formula", {})
        wounds_formula = wounds_document.get("formula", {})
        toughness_modifier = characteristic_modifiers["TOU"]
        mythic_toughness = mythic_value(character.mythic_characteristics.get("TOU", 0))
        toughness_multiplier = self._rule_multiplier(
            wounds_formula.get("toughness_modifier", "Add Toughness Modifier * 2"),
            WOUNDS_PER_TOUGHNESS_MODIFIER,
        )
        mythic_toughness_multiplier = self._rule_multiplier(
            wounds_formula.get("mythic_toughness", "Add Mythic Toughness * 2"),
            WOUNDS_PER_MYTHIC_TOUGHNESS,
        )
        robust_count = selected_outlier_names.count("Robust")
        wounds_total = max_wounds(
            character.characteristics["TOU"],
            mythic_toughness,
            robust_count,
            base=wounds_formula.get("base", WOUNDS_BASE),
            toughness_multiplier=toughness_multiplier,
            mythic_multiplier=mythic_toughness_multiplier,
        )
        lines.append(
            f"Wounds ({wounds_document.get('calculation', '40 + (Toughness Modifier × 2) + (Mythic Toughness × 2)')}): "
            f"{wounds_formula.get('base', WOUNDS_BASE)} + ({toughness_modifier} × {toughness_multiplier}) + "
            f"({mythic_toughness} × {mythic_toughness_multiplier}) + "
            f"Robust {robust_count} × {ROBUST_WOUNDS} = {wounds_total}"
        )
        lines.append(
            f"Character model Wounds value: {character.wounds}"
        )

        perception_document = (
            self.game_data.get("perceptive_range", "perceptive_range") or {}
        ).get("perceptive_range", {})
        base_formula = perception_document.get("base_formula", "perception * 2")
        base_multiplier = self._rule_multiplier(base_formula, 2)
        vigil_effect = self._outlier_record("Vigil").get("effect", "")
        vigil_bonus = (
            int(
                vigil_effect.rsplit("by", 1)[1]
                .strip()
                .split()[0]
                .rstrip(".")
            )
            if "Vigil" in selected_outlier_names
            else 0
        )
        perception_multiplier = base_multiplier + vigil_bonus
        perception = character.characteristics["PER"]
        lines.append(
            f"Perceptive range (Perception × {base_multiplier}"
            f"{f' + Vigil {vigil_bonus}' if vigil_bonus else ''}): {perception} m × "
            f"{perception_multiplier} = {perception * perception_multiplier} m"
        )

        encumbrance_document = (
            self.game_data.get("encumbrance", "encumbrance") or {}
        ).get("encumbrance", {})
        carry_formula = encumbrance_document.get(
            "carry_weight", "Half of Strength + Toughness"
        )
        strongman = "Strongman" in selected_outlier_names
        mythic_document = (
            self.game_data.get(
                "mythic_characteristics", "mythic_characteristics"
            )
            or {}
        ).get("mythic", {})
        strength_carry_bonus = mythic_document.get("strength", {}).get(
            "carry_weight_bonus", "X * 10"
        )
        toughness_carry_bonus = mythic_document.get("toughness", {}).get(
            "carry_weight_bonus", "X * 10"
        )
        strength_bonus_multiplier = self._rule_multiplier(
            strength_carry_bonus, 10
        )
        toughness_bonus_multiplier = self._rule_multiplier(
            toughness_carry_bonus, 10
        )
        spartan = any(
            trait.get("name") == "Carry Weight"
            and "Doubles Strength and Toughness" in trait.get("effect", "")
            for trait in (
                self.game_data.get("soldier_type", character.soldier_type) or {}
            ).get("traits", [])
        )
        strength_value = (
            character.characteristics["STR"]
            + self._mythic_value(character, "STR") * strength_bonus_multiplier
        )
        toughness_value = (
            character.characteristics["TOU"]
            + self._mythic_value(character, "TOU") * toughness_bonus_multiplier
        )
        if spartan:
            strength_value *= 2
            toughness_value *= 2
        carry_weight = (
            strength_value + toughness_value
            if strongman
            else (strength_value + toughness_value) / 2
        )
        lines.append(
            f"Carry weight ({carry_formula}; Mythic bonuses "
            f"STR {strength_carry_bonus}, TOU {toughness_carry_bonus}"
            f"{'; Spartan doubling' if spartan else ''}"
            f"{'; Strongman removes halving' if strongman else ''}): "
            f"({strength_value:g} + {toughness_value:g})"
            f"{'' if strongman else ' / 2'} = {carry_weight:g}"
        )
        lift_formula = encumbrance_document.get("lift_weight", "Carry Weight * 3")
        push_formula = encumbrance_document.get("push_weight", "Carry Weight * 5")
        lift_weight = carry_weight * self._rule_multiplier(lift_formula, 3)
        push_weight = carry_weight * self._rule_multiplier(push_formula, 5)
        lines.append(
            f"Lift weight ({lift_formula}): "
            f"{lift_weight:g}"
        )
        lines.append(
            f"Push weight ({push_formula}): "
            f"{push_weight:g}"
        )

        lines.extend(("", "GENERATOR LOG", *character.debug_log))
        return "\n".join(lines)
