class BaseValidator:
    """
    Shared validation helpers used by all document validators.
    """

    CHARACTERISTIC_CODES = {
        "STR", "TOU", "AGI", "WFR", "WFM",
        "INT", "PER", "CRG", "CHA", "LDR"
    }

    def __init__(self, game_data):
        self.game_data = game_data

    def require(self, condition, message):
        if not condition:
            self.game_data.record_error(message)

    def validate_characteristic_map(self, path, cmap):
        if not isinstance(cmap, dict):
            self.game_data.record_error(f"{path}: must be an object")
            return

        for key, value in cmap.items():
            if key not in self.CHARACTERISTIC_CODES:
                self.game_data.record_error(
                    f"{path}: invalid characteristic '{key}'"
                )

            if not (
                isinstance(value, (int, float, str)) or value is None
            ):
                self.game_data.record_error(
                    f"{path}.{key}: must be number|string|null"
                )
