# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Light & Sky aspects, abilities, grenades and supers.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""
from src.models.xp_shop import starting_aspect_slots, starting_light_ability_slots

class LightPowersMixin:
    def select_light_category(self, category):
        self._selected_light_category = category
        self._build_light_power_tiles()

    def _build_light_power_tiles(self):
        self._clear_equipment_grid()
        self.equipment_tiles.clear()
        self.light_aspect_tiles.clear()
        self.light_ability_tiles.clear()
        self.equipment_page.set_light_mode(True)
        self.equipment_page_title.setText("LIGHT ASPECTS AND ABILITIES")

        aspects_document = self.game_data.get("light_aspects", "light_aspects") or {}
        aspects_by_connection = aspects_document.get("light_aspects", {})
        selected_connection = self.connection_combo.currentText()
        selected_connection_group = self._connection_group(selected_connection)
        selected_class = self.guardian_combo.currentData() or ""
        ability_document = self.game_data.get(
            "light_abilities", "light_abilities_and_grenades"
        ) or {}
        abilities = ability_document.get("abilities", [])
        grenades = ability_document.get("grenades", [])
        ability_rules = self.game_data.get(
            "light_ability_rules", "light_ability_rules"
        ) or {}
        light_ability_rules = ability_rules.get("light_abilities", {})
        super_rules = light_ability_rules["supers"]
        grenade_super_rule = light_ability_rules["grenade_supers"]["rule"]

        all_aspects = [
            (connection.title(), aspect)
            for connection, records in aspects_by_connection.items()
            if isinstance(records, list)
            for aspect in records
            if self._matches_selected_connection(
                aspect,
                selected_connection,
                selected_connection_group,
                fallback_connection=connection,
            )
        ]

        available_powers = [
            (ability, "Light Ability")
            for ability in abilities
            if self._matches_selected_connection(
                ability, selected_connection, selected_connection_group
            )
            and (
                str(ability.get("class", "")).strip().casefold() == "all"
                or str(ability.get("class", "")).strip().casefold()
                == str(selected_class).strip().casefold()
            )
        ]
        available_powers.extend(
            (grenade, "Light Grenade")
            for grenade in grenades
            if self._matches_selected_connection(
                grenade, selected_connection, selected_connection_group
            )
        )

        valid_aspect_keys = {
            (connection.casefold(), aspect["name"].casefold())
            for connection, aspect in all_aspects
        }
        valid_power_keys = {
            (power_type, power["name"].casefold())
            for power, power_type in available_powers
        }
        self._selected_light_aspects = {
            key: value
            for key, value in self._selected_light_aspects.items()
            if key in valid_aspect_keys
        }
        self._selected_light_powers = {
            key: value
            for key, value in self._selected_light_powers.items()
            if key in valid_power_keys
        }
        self._selected_light_supers = {
            key: value
            for key, value in self._selected_light_supers.items()
            if key in valid_power_keys
        }
        # Switching away from a Warlock, or dropping Passive / Focus, can leave
        # more picks than slots
        power_limit = self._light_power_slot_limit()
        if len(self._selected_light_powers) > power_limit:
            self._selected_light_powers = dict(
                list(self._selected_light_powers.items())[:power_limit]
            )
        aspect_limit = self._light_aspect_slot_limit()
        if len(self._selected_light_aspects) > aspect_limit:
            self._selected_light_aspects = dict(
                list(self._selected_light_aspects.items())[:aspect_limit]
            )

        if self._selected_light_category == "aspects":
            self.equipment_page.options_title.setText("Light Aspects")
            aspect_limit = self._light_aspect_slot_limit()
            outlier_note = (
                " (includes the Passive Outlier's extra Aspect)"
                if aspect_limit > starting_aspect_slots(self.game_data)
                else ""
            )
            self.equipment_page.options_description.setText(
                f"Select up to {aspect_limit} Light Aspect"
                f"{'s' if aspect_limit != 1 else ''} - one per Aspect Slot{outlier_note}."
            )
            for index, (connection, aspect) in enumerate(all_aspects):
                key = (connection.casefold(), aspect["name"].casefold())
                tile, select_button = self._create_selection_tile(
                    aspect["name"],
                    f"{connection} | XP {self._light_aspect_cost(aspect, connection)}\n"
                    f"{aspect['description']}",
                    min_height=145,
                )
                select_button.toggled.connect(
                    lambda checked, selected_tile=select_button, selected_key=key,
                    selected_aspect=aspect, selected_connection_name=connection:
                    self._select_light_tile(
                        selected_tile,
                        "aspect",
                        checked,
                        selected_key,
                        (selected_aspect, selected_connection_name),
                    )
                )
                self.light_aspect_tiles.append(
                    (select_button, aspect, connection)
                )
                select_button.setChecked(key in self._selected_light_aspects)
                self.equipment_grid.addWidget(tile, index // 3, index % 3)
        elif self._selected_light_category == "powers":
            self.equipment_page.options_title.setText("Light Abilities / Grenades")
            power_limit = self._light_power_slot_limit()
            guardian = self._selected_guardian_record() or {}
            class_name = str(guardian.get("name") or "class").split()[0]
            extras = []
            if self._light_power_class_bonus():
                extras.append(
                    f"{self._light_power_class_bonus()} extra from the "
                    f"{class_name} Power trait"
                )
            outlier_bonus = power_limit - starting_light_ability_slots(
                self.game_data, self._selected_guardian_record()
            )
            if outlier_bonus:
                extras.append(f"{outlier_bonus} extra from the Focus Outlier")
            class_note = f" ({'; '.join(extras)})" if extras else ""
            self.equipment_page.options_description.setText(
                f"Select up to {power_limit} Light Abilities and/or Light Grenades"
                f" - one per Light Ability Slot{class_note}."
            )
            power_selection = self._selected_light_powers
        elif self._selected_light_category == "supers":
            self.equipment_page.options_title.setText("Supers")
            self.equipment_page.options_description.setText(
                "Select one Super. Cost: "
                f"{super_rules['experience_cost_multiplier']:g}x XP and "
                f"{super_rules['energy_cost_multiplier']:g}x Energy."
            )
            power_selection = self._selected_light_supers
        else:
            power_selection = None

        if self._selected_light_category in {"powers", "supers"}:
            for index, (power, power_type) in enumerate(available_powers):
                description = power.get("description") or power.get("special_rules", "")
                is_super = self._selected_light_category == "supers"
                experience_cost = (
                    self._super_experience_cost(
                        power, super_rules["experience_cost_multiplier"]
                    )
                    if is_super
                    else int(power.get("experience_cost", 0) or 0)
                )
                energy_cost = power.get("light_cost", "N/A")
                if is_super:
                    energy_cost = self._super_energy_cost(
                        energy_cost, super_rules["energy_cost_multiplier"]
                    )
                    tile_details = (
                        f"{power_type} Super | XP {experience_cost} | "
                        f"Super Energy {energy_cost}"
                    )
                else:
                    tile_details = (
                        f"{power_type} | XP {experience_cost} | "
                        f"Light {energy_cost}"
                    )
                if power_type == "Light Grenade":
                    damage_parts = [
                        str(power[field])
                        for field in ("damage_roll", "base_damage")
                        if power.get(field) is not None
                    ]
                    damage = " + ".join(damage_parts) if damage_parts else "None"
                    tile_details += (
                        f"\nDamage: {damage} | Range: {power.get('range') or 'N/A'}"
                    )
                    second = power.get("second_detonation")
                    if isinstance(second, dict):
                        second_damage = " + ".join(
                            str(second[field])
                            for field in ("damage_roll", "base_damage")
                            if second.get(field) is not None
                        ) or "None"
                        tile_details += (
                            f"\nSecond detonation: {second_damage} | "
                            f"Range: {second.get('range') or 'N/A'}"
                        )
                    if is_super:
                        tile_details += f"\nSuper effect: {grenade_super_rule}"
                if is_super:
                    super_description = power.get("super_description") or (
                        grenade_super_rule
                        if power_type == "Light Grenade"
                        else "No Super description is specified in the data."
                    )
                    tile_details += (
                        f"\nRegular description: {description}"
                        f"\nSuper description: {super_description}"
                    )
                else:
                    tile_details += f"\n{description}"
                power_data = dict(power)
                if is_super:
                    power_data["experience_cost"] = experience_cost
                    power_data["super_energy_cost"] = energy_cost
                    power_data["super_description"] = super_description
                    power_data["_power_type"] = (
                        "Super Grenade"
                        if power_type == "Light Grenade"
                        else "Super Ability"
                    )
                else:
                    power_data["description"] = description
                    power_data["_power_type"] = power_type
                key = (power_type, power["name"].casefold())
                tile, select_button = self._create_selection_tile(
                    power["name"],
                    tile_details,
                    min_height=145,
                )
                select_button.toggled.connect(
                    lambda checked, selected_tile=select_button,
                    selected_key=key, selected_power=power_data:
                    self._select_light_tile(
                        selected_tile,
                        "super" if is_super else "power",
                        checked,
                        selected_key,
                        selected_power,
                    )
                )
                self.light_ability_tiles.append((select_button, power_data))
                select_button.setChecked(key in power_selection)
                self.equipment_grid.addWidget(tile, index // 3, index % 3)
        elif self._selected_light_category not in {"aspects", "powers", "supers"}:
            self.equipment_page.options_title.setText("Select a category")
            self.equipment_page.options_description.setText(
                "Choose Light Aspects, Light Abilities / Grenades, or Supers to view options."
            )
        self.update_light_power_selection()

    def _select_light_tile(
        self, selected_tile, selection_kind, checked, selection_key, selected_value
    ):
        selections = (
            self._selected_light_aspects
            if selection_kind == "aspect"
            else (
                self._selected_light_supers
                if selection_kind == "super"
                else self._selected_light_powers
            )
        )
        if selection_kind == "super":
            limit = 1
        elif selection_kind == "aspect":
            limit = self._light_aspect_slot_limit()
        else:
            limit = self._light_power_slot_limit()
        if (
            checked
            and selection_key not in selections
            and len(selections) >= limit
        ):
            selected_tile.blockSignals(True)
            selected_tile.setChecked(False)
            selected_tile.blockSignals(False)
        elif checked:
            selections[selection_key] = selected_value
            if self._selected_light_xp_cost() > self._light_xp_budget():
                selections.pop(selection_key, None)
                selected_tile.blockSignals(True)
                selected_tile.setChecked(False)
                selected_tile.blockSignals(False)
        else:
            selections.pop(selection_key, None)
        self._update_light_xp_display()
        self.update_light_power_selection()

    def update_light_power_selection(self):
        aspect_count = len(self._selected_light_aspects)
        ability_count = len(self._selected_light_powers)
        super_count = len(self._selected_light_supers)
        self._update_light_xp_display()
        self.equipment_done_button.setText(
            f"Done (Aspects {aspect_count}/{self._light_aspect_slot_limit()}; "
            f"Light Powers {ability_count}/{self._light_power_slot_limit()}; "
            f"Supers {super_count}/1)"
        )

    def finish_light_power_selection(self):
        if hasattr(self, "generated_character"):
            aspects = [
                aspect_and_connection[0]
                for aspect_and_connection in self._selected_light_aspects.values()
            ]
            abilities = list(self._selected_light_powers.values())
            supers = list(self._selected_light_supers.values())
            self.generated_character.apply_light_powers(aspects, abilities, supers)
            current_budget = (
                self.generated_character.experience + self._light_xp_spent
            )
            new_xp_spent = self._selected_light_xp_cost()
            self.generated_character.experience = current_budget - new_xp_spent
            self.generated_character.experience_spent += (
                new_xp_spent - self._light_xp_spent
            )
            self._light_xp_spent = new_xp_spent
        self.character_setup_home.set_character_ready_to_export(True)
        self.pages.setCurrentWidget(self.character_setup_home)

    def _selected_guardian_record(self):
        key = self.guardian_combo.currentData()
        if not key:
            return None
        record = self.game_data.get("soldier_type", key)
        return record if isinstance(record, dict) else None

    def _light_power_class_bonus(self):
        """Free Light Ability Slots from the chosen Guardian class (Warlock: 1)."""
        return starting_light_ability_slots(
            self.game_data, self._selected_guardian_record()
        ) - starting_light_ability_slots(self.game_data, None)

    def _chosen_outliers(self):
        """Outliers picked so far (Passive and Focus add creation picks)."""
        character = getattr(self, "generated_character", None)
        return list(getattr(character, "outliers", None) or [])

    def _light_power_slot_limit(self):
        """Light Abilities / Grenades a new character can take: one per starting slot."""
        return starting_light_ability_slots(
            self.game_data, self._selected_guardian_record(), self._chosen_outliers()
        )

    def _light_aspect_slot_limit(self):
        """Light Aspects a new character can take: one per starting Aspect Slot."""
        return starting_aspect_slots(
            self.game_data, self._selected_guardian_record(), self._chosen_outliers()
        )

    def _light_aspect_cost(self, aspect, connection):
        selected_connection = self.connection_combo.currentText()
        cost = aspect.get("experience_cost", 0)
        return (
            cost
            if connection.strip().casefold() == selected_connection.strip().casefold()
            else cost * 2
        )

    def _light_power_xp_cost(self, power):
        return int(power.get("experience_cost", 0) or 0)

    @staticmethod
    def _super_experience_cost(power, multiplier):
        return int(power.get("experience_cost", 0) * multiplier)

    @staticmethod
    def _super_energy_cost(light_cost, multiplier):
        if isinstance(light_cost, (int, float)):
            return light_cost * multiplier
        return f"{multiplier} x {light_cost}"

    def _selected_light_xp_cost(self):
        aspect_cost = sum(
            self._light_aspect_cost(aspect, connection)
            for aspect, connection in self._selected_light_aspects.values()
        )
        power_cost = sum(
            self._light_power_xp_cost(power)
            for power in self._selected_light_powers.values()
        )
        super_cost = sum(
            self._light_power_xp_cost(power)
            for power in self._selected_light_supers.values()
        )
        return aspect_cost + power_cost + super_cost

    def _light_xp_budget(self):
        if hasattr(self, "generated_character"):
            return self.generated_character.experience + self._light_xp_spent
        return self.experience_input.value()

    def _update_light_xp_display(self):
        available_xp = self._light_xp_budget()
        spent_xp = self._selected_light_xp_cost()
        self.equipment_page.experience_remaining_label.setText(
            f"XP remaining: {available_xp - spent_xp:,} / {available_xp:,}"
        )

        xp_left = available_xp - spent_xp
        for button, aspect, connection in self.light_aspect_tiles:
            cost = self._light_aspect_cost(aspect, connection)
            button.setEnabled(button.isChecked() or cost <= xp_left)
        for button, power in self.light_ability_tiles:
            cost = self._light_power_xp_cost(power)
            button.setEnabled(button.isChecked() or cost <= xp_left)

    def _connection_group(self, selected_connection):
        selected = selected_connection.strip().casefold()
        connections_document = self.game_data.get("connections", "connections") or {}
        connections = connections_document.get("connections", connections_document)
        for group in ("light", "darkness", "specialized"):
            for connection in connections.get(group, []):
                if connection.get("name", "").strip().casefold() == selected:
                    return group
        return ""

    @staticmethod
    def _matches_selected_connection(
        record,
        selected_connection,
        selected_connection_group="",
        fallback_connection=None,
    ):
        selected = selected_connection.strip().casefold()
        selected_group = selected_connection_group.strip().casefold()
        connection_values = [record.get("connection")]
        group_values = [record.get("group")]
        if fallback_connection is not None:
            connection_values.append(fallback_connection)

        for value in connection_values + group_values:
            if isinstance(value, str):
                values = (value,)
            elif isinstance(value, (list, tuple, set)):
                values = value
            else:
                continue
            for candidate in values:
                if not isinstance(candidate, str):
                    continue
                normalized = candidate.strip().casefold()
                if normalized == "universal" or (
                    (selected and normalized == selected)
                    or (selected_group and normalized == selected_group)
                ):
                    return True
        return False
