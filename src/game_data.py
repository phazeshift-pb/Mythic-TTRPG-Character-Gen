import json
from pathlib import Path


class GameData:
    """
    Unified container for all Mythic TTRPG JSON data.
    Every loader populates this object.
    """

    def __init__(self):
        self.documents = {}          # raw JSON by path
        self.families = {}           # grouped by document type
        self.errors = []             # validation errors

    def add_document(self, family: str, name: str, data: dict):
        if family not in self.families:
            self.families[family] = {}

        self.families[family][name] = data

    def get(self, family: str, name: str):
        return self.families.get(family, {}).get(name)

    def list(self, family: str):
        return list(self.families.get(family, {}).keys())

    def record_error(self, message: str):
        self.errors.append(message)

    def has_errors(self):
        return len(self.errors) > 0

    def print_errors(self):
        print("\n❌ Validation Errors:")
        for err in self.errors:
            print("  -", err)