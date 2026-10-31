"""Soldier type, background, lifestyle and Light & Sky setup choices.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

import re

from PySide6.QtWidgets import QDialog, QMessageBox

from src.data_loader import DataLoader
from src.models.background_choices import choice_groups, describe
from src.ui.background_choice_dialog import BackgroundChoiceDialog
from src.ui.skill_training_dialog import SkillTrainingDialog


class InitialSetupMixin:
    def _handle_version_selection_changed(self, mode):
        self.character_setup_home.set_version_selected(mode is not None)
        self.character_setup_home.set_character_ready_to_export(False)
        self.update_soldier_types()

    def _refresh_initial_setup_options(self):
        if not hasattr(self, "game_data"):
            return

        page = self.initial_character_setup_page
        if self.selected_mode == "Light & Sky":
            categories = (
                ("human", "Human Soldier Type"),
                ("guardian", "Guardian Soldier Type"),
                ("subclass", "Subclass"),
                ("connection", "Connection"),
            )
            option_combos = {
                "human": self.human_combo,
                "guardian": self.guardian_combo,
                "subclass": self.subclass_combo,
                "connection": self.connection_combo,
            }
        else:
            categories = (
                ("soldier", "Soldier Type"),
                ("upbringing", "Upbringing"),
                ("environment", "Environment"),
                ("lifestyles", "Lifestyles"),
            )
            option_combos = {
                "soldier": self.soldier_combo,
                "upbringing": self.upbringing_combo,
                "environment": self.environment_combo,
                "lifestyles": self.lifestyle_combos[0],
            }

        page.set_categories(categories)
        for category, label in categories:
            combo = option_combos[category]
            combos = self.lifestyle_combos if category == "lifestyles" else (combo,)
            options = []
            selected_values = []
            for option_combo in combos:
                for index in range(option_combo.count()):
                    value = option_combo.itemData(index)
                    if value is None:
                        value = option_combo.itemText(index)
                    if not value:
                        continue
                    if not any(
                        existing_value == value
                        for _, existing_value, _ in options
                    ):
                        options.append(
                            (
                                option_combo.itemText(index),
                                value,
                                self._format_initial_setup_option(
                                    category, value
                                ),
                            )
                        )
                value = option_combo.currentData()
                if value is None:
                    value = option_combo.currentText()
                if value:
                    selected_values.append(value)
            page.set_category_options(
                category,
                label,
                options,
                selected_values,
            )

    def _format_initial_setup_option(self, category, value):
        record = None
        if category in {"soldier", "human", "guardian"}:
            record = self.game_data.get("soldier_type", value)
        elif category in {"upbringing", "environment", "lifestyles"}:
            family = "lifestyle" if category == "lifestyles" else category
            document = self.game_data.get(family, family) or {}
            record = next(
                (
                    item
                    for item in document.get(family, [])
                    if item.get("name") == value
                ),
                None,
            )
        elif category == "subclass":
            guardian = self.game_data.get(
                "soldier_type", self.guardian_combo.currentData()
            ) or {}
            record = guardian.get("subclasses", {}).get(value)
        elif category == "connection":
            document = self.game_data.get("connections", "connections") or {}
            connections = document.get("connections", document)
            record = next(
                (
                    connection
                    for group in ("light", "darkness", "specialized")
                    for connection in connections.get(group, [])
                    if connection.get("name") == value
                ),
                None,
            )

        if not record:
            return "No additional details."

        sections = []
        if record.get("experience_cost") is not None:
            sections.append(f"Experience Cost: {record['experience_cost']:,} XP")
        for key, heading in (
            ("base_characteristics", "Base Characteristics"),
            ("mythic_characteristics", "Mythic Characteristics"),
            ("advancements", "Advancements"),
            ("characteristic_modifiers", "Characteristic Modifiers"),
        ):
            values = record.get(key)
            if isinstance(values, dict):
                entries = [
                    f"{code}: {amount}"
                    for code, amount in values.items()
                    if amount is not None
                ]
                if entries:
                    sections.append(f"{heading}: {', '.join(entries)}")

        traits = record.get("traits", [])
        if traits:
            trait_details = []
            for trait in traits:
                if isinstance(trait, dict):
                    name = trait.get("name", "Trait")
                    effect = trait.get("effect")
                    trait_details.append(
                        f"{name}: {effect}" if effect else name
                    )
                else:
                    trait_details.append(str(trait))
            sections.append("Traits: " + "; ".join(trait_details))

        for key, heading in (("bonuses", "Bonuses"), ("penalties", "Penalties")):
            values = record.get(key, [])
            if values:
                sections.append(f"{heading}: {', '.join(describe(values))}")

        if category == "lifestyles":
            for outcome in record.get("outcomes", []):
                outcome_details = [f"Roll {outcome.get('roll', '?')}"]
                for key, heading in (
                    ("bonuses", "Bonuses"),
                    ("penalties", "Penalties"),
                ):
                    values = outcome.get(key, [])
                    if values:
                        outcome_details.append(
                            f"{heading}: {', '.join(map(str, values))}"
                        )
                sections.append(" | ".join(outcome_details))

        if record.get("information"):
            sections.append(f"Information: {record['information']}")
        if record.get("training"):
            sections.append(f"Training: {', '.join(record['training'])}")

        return "\n".join(sections) if sections else "No additional details."

    def _background_record(self, category, name):
        document = self.game_data.get(category, category) or {}
        return next(
            (
                record
                for record in document.get(category, [])
                if name and record.get("name", "").casefold() == str(name).casefold()
            ),
            None,
        )

    def _background_choices_for(self, category, name):
        stored = self._background_choices.get(category) or {}
        return list(stored.get("choices", [])) if stored.get("name") == name else []

    def _prompt_background_choices(self, category, name):
        """Ask for this background's either/or picks. False if the player cancels."""
        record = self._background_record(category, name)
        groups = choice_groups(record) if record else []
        if not groups:
            self._background_choices.pop(category, None)
            return True
        dialog = BackgroundChoiceDialog(
            record["name"],
            groups,
            selected=self._background_choices_for(category, name),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        self._background_choices[category] = {
            "name": name,
            "choices": dialog.selected_choices,
        }
        return True

    def _ensure_background_choices(self):
        """Before generating, make sure every chosen background has its picks."""
        for category, combo in (
            ("upbringing", self.upbringing_combo),
            ("environment", self.environment_combo),
        ):
            name = combo.currentData()
            record = self._background_record(category, name)
            needed = len(choice_groups(record)) if record else 0
            if needed and len(self._background_choices_for(category, name)) != needed:
                if not self._prompt_background_choices(category, name):
                    return False
        return True

    def select_initial_setup_option(self, category, value, checked):
        if checked and category in {"upbringing", "environment"}:
            if not self._prompt_background_choices(category, value):
                self._refresh_initial_setup_options()
                return
        if checked and category in {"soldier", "human", "guardian"}:
            soldier_data = self.game_data.get("soldier_type", value) or {}
            try:
                requirements = self._skill_training_requirements(soldier_data)
                if requirements:
                    skill_count, training_bonus = requirements
                    skills_document = self.game_data.get("skills", "skills") or {}
                    skill_names = [
                        skill.get("name")
                        for skill in skills_document.get("skills", [])
                        if skill.get("name")
                    ]
                    previous_selection = self._selected_soldier_skills.get(
                        value, {}
                    )
                    dialog = SkillTrainingDialog(
                        skill_names,
                        skill_count,
                        training_bonus,
                        selected_skills=previous_selection,
                        parent=self,
                    )
                    if dialog.exec() != QDialog.DialogCode.Accepted:
                        self._refresh_initial_setup_options()
                        return
                    self._selected_soldier_skills[value] = {
                        skill: training_bonus
                        for skill in dialog.selected_skills
                    }
            except ValueError as error:
                QMessageBox.warning(
                    self,
                    "Skill Training Selection",
                    str(error),
                )
                self._refresh_initial_setup_options()
                return

        if category == "lifestyles":
            if checked:
                matching_combo = next(
                    (combo for combo in self.lifestyle_combos if not combo.currentData()),
                    None,
                )
                if matching_combo is None:
                    self._refresh_initial_setup_options()
                    return
                index = matching_combo.findData(value)
            else:
                matching_combo = next(
                    (
                        combo
                        for combo in reversed(self.lifestyle_combos)
                        if (combo.currentData() or combo.currentText()) == value
                    ),
                    None,
                )
                if matching_combo is None:
                    return
                index = 0
        else:
            combo = {
                "soldier": self.soldier_combo,
                "human": self.human_combo,
                "guardian": self.guardian_combo,
                "upbringing": self.upbringing_combo,
                "environment": self.environment_combo,
                "subclass": self.subclass_combo,
                "connection": self.connection_combo,
            }[category]
            index = combo.findData(value)
            if index < 0:
                index = combo.findText(value)
        if index >= 0:
            if category == "lifestyles":
                matching_combo.setCurrentIndex(index)
            else:
                combo.setCurrentIndex(index)
        self._refresh_initial_setup_options()

    @staticmethod
    def _skill_training_requirements(soldier_data):
        skill_trait = next(
            (
                trait
                for trait in soldier_data.get("traits", [])
                if isinstance(trait, dict)
                and isinstance(trait.get("name"), str)
                and trait["name"].casefold() == "skill training"
            ),
            None,
        )
        if skill_trait is None:
            return None

        effect = skill_trait.get("effect")
        if not isinstance(effect, str):
            raise ValueError("The Skill Training trait is missing its effect text.")

        number_words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        count_match = re.search(
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s+skills?\b",
            effect,
            re.IGNORECASE,
        )
        level_match = re.search(
            r"\bat\s+(Trained|\+\d+)\b",
            effect,
            re.IGNORECASE,
        )
        if not count_match or not level_match:
            raise ValueError(
                "The Skill Training trait must specify a skill count and training level."
            )

        count_text = count_match.group(1).casefold()
        skill_count = number_words.get(count_text)
        if skill_count is None:
            skill_count = int(count_text)
        level_text = level_match.group(1)
        training_bonus = (
            0 if level_text.casefold() == "trained" else int(level_text[1:])
        )
        if (
            skill_count < 1
            or training_bonus < 0
            or training_bonus > 20
            or training_bonus % 10
        ):
            raise ValueError(
                "The Skill Training trait specifies an unsupported count or training level."
            )
        return skill_count, training_bonus

    # ---------------------------------------------------------
    # Load soldier types based on mode
    # ---------------------------------------------------------
    def update_soldier_types(self):
        use_lns = self.selected_mode == "Light & Sky"
        self._selected_soldier_skills.clear()
        self.character_setup_home.equipment_or_light_powers_button.setText(
            "Light Abilities / Light Aspects" if use_lns else "Equipment"
        )
        loader = DataLoader(use_light_and_sky=use_lns)
        self.game_data = loader.load_all()
        self._load_creation_point_options()
        self.update_experience_tier()

        soldier_types = self.game_data.families.get("soldier_type", {})

        core_list = []
        human_list = []
        guardian_list = []

        for name, record in soldier_types.items():
            path = record.get("source_path", "")

            if "core/unsc_soldier_types" in path:
                core_list.append(name)

            if "light_and_sky/character_creation/human_soldier_types" in path:
                human_list.append(name)

            if "light_and_sky/character_creation/guardian_classes_subclasses" in path:
                guardian_list.append(name)

        self._core_names = core_list
        self._human_names = human_list
        self._guardian_names = guardian_list
        self.subclass_combo.clear()
        self.connection_combo.clear()

        if use_lns:
            self.connection_combo.addItem("")
            connections = self.game_data.get("connections", "connections") or {}
            connections = connections.get("connections", connections)
            for category in ("light", "darkness", "specialized"):
                self.connection_combo.addItems(
                    [item["name"] for item in connections.get(category, [])]
                )
        self.refresh_selection_options()
        self.update_subclasses()
        self._refresh_initial_setup_options()
        self._build_outlier_tiles()
        if use_lns:
            self._build_light_power_tiles()
        else:
            self._build_equipment_tiles()
        self.update_specialization_selection()

    @staticmethod
    def _add_costed_items(combo, names, records, available_xp):
        combo.addItem("")
        for name in names:
            cost = records[name].get("experience_cost", 0)
            if cost <= available_xp:
                combo.addItem(f"{records[name].get('name', name)} ({cost:,} XP)", name)

    def refresh_selection_options(self):
        if (
            not hasattr(self, "game_data")
            or not hasattr(self, "_core_names")
            or getattr(self, "_refreshing_options", False)
        ):
            return

        self._refreshing_options = True
        try:
            records = self.game_data.families.get("soldier_type", {})
            available_xp = self.experience_input.value()
            use_lns = self.selected_mode == "Light & Sky"
            selected_human = self.human_combo.currentData()
            selected_guardian = self.guardian_combo.currentData()

            self.soldier_combo.clear()
            self.human_combo.clear()
            self.guardian_combo.clear()

            if use_lns:
                self._add_costed_items(
                    self.human_combo, self._human_names, records, available_xp
                )
                human_cost = records.get(selected_human, {}).get("experience_cost", 0)
                guardian_xp = max(0, available_xp - human_cost)
                self._add_costed_items(
                    self.guardian_combo, self._guardian_names, records, guardian_xp
                )
                self._restore_combo_selection(self.human_combo, selected_human)
                self._restore_combo_selection(self.guardian_combo, selected_guardian)
            else:
                self._add_costed_items(
                    self.soldier_combo, self._core_names, records, available_xp
                )
                self.refresh_core_background_options()
            if use_lns:
                self.update_subclasses()
        finally:
            self._refreshing_options = False
        self._refresh_initial_setup_options()

    def refresh_core_background_options(self):
        if (
            not hasattr(self, "game_data")
            or getattr(self, "_refreshing_background_options", False)
            or self.selected_mode != "Core"
        ):
            return

        self._refreshing_background_options = True
        try:
            selected_upbringing = self.upbringing_combo.currentData()
            selected_environment = self.environment_combo.currentData()
            selected_lifestyles = [combo.currentData() for combo in self.lifestyle_combos]

            upbringing_records = (
                self.game_data.get("upbringing", "upbringing") or {}
            ).get("upbringing", [])
            environment_records = (
                self.game_data.get("environment", "environment") or {}
            ).get("environment", [])
            lifestyle_records = (
                self.game_data.get("lifestyle", "lifestyle") or {}
            ).get("lifestyle", [])

            self.upbringing_combo.blockSignals(True)
            self.environment_combo.blockSignals(True)
            for combo in self.lifestyle_combos:
                combo.blockSignals(True)
            self.upbringing_combo.clear()
            self.environment_combo.clear()
            for combo in self.lifestyle_combos:
                combo.clear()

            self.upbringing_combo.addItem("", "")
            for record in upbringing_records:
                self.upbringing_combo.addItem(record["name"], record["name"])
            self._restore_combo_selection(self.upbringing_combo, selected_upbringing)

            selected_record = next(
                (
                    record
                    for record in upbringing_records
                    if record["name"] == self.upbringing_combo.currentText()
                ),
                None,
            )
            available_environments = (
                selected_record.get("environment_available", ["Any"])
                if selected_record
                else ["Any"]
            )
            self.environment_combo.addItem("", "")
            for record in environment_records:
                if (
                    "Any" in available_environments
                    or record["name"] in available_environments
                ):
                    self.environment_combo.addItem(
                        record["name"], record["name"]
                    )
            self._restore_combo_selection(self.environment_combo, selected_environment)

            for combo, selected_lifestyle in zip(
                self.lifestyle_combos, selected_lifestyles
            ):
                combo.addItem("", "")
                for record in lifestyle_records:
                    combo.addItem(record["name"], record["name"])
                self._restore_combo_selection(combo, selected_lifestyle)
        finally:
            self.upbringing_combo.blockSignals(False)
            self.environment_combo.blockSignals(False)
            for combo in self.lifestyle_combos:
                combo.blockSignals(False)
            self._refreshing_background_options = False
        self._refresh_initial_setup_options()

    @staticmethod
    def _restore_combo_selection(combo, key):
        if key is None:
            return
        index = combo.findData(key)
        if index >= 0:
            combo.setCurrentIndex(index)

    # ---------------------------------------------------------
    # Populate subclasses when a Guardian class is selected
    # ---------------------------------------------------------
    def update_subclasses(self):
        self.subclass_combo.clear()

        soldier_type = self.guardian_combo.currentData()
        if not soldier_type:
            self._refresh_initial_setup_options()
            return

        record = self.game_data.get("soldier_type", soldier_type)
        if not record:
            self._refresh_initial_setup_options()
            return

        path = record.get("source_path", "")

        # Only Guardian classes have subclasses
        if "guardian_classes_subclasses" in path:
            subclasses = record.get("subclasses", {})
            self.subclass_combo.addItems(list(subclasses.keys()))
        else:
            # No subclasses for UNSC or Human soldier types
            self.subclass_combo.clear()
        self._refresh_initial_setup_options()
