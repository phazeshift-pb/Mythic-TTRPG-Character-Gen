"""D100 Tests (Mythic 7.0 CU1, Tests and Dice Rolls, p. 6; To Hit Test).

* Roll a D100: equal to or under the modified Characteristic succeeds.
* Each full 10 points under the target is a Degree of Success; each full
  10 points over is a Degree of Failure ("Success with 0 Degrees" is possible).
* Natural 1 is a Critical Success: always succeeds, with at least as many
  Degrees of Success as the Characteristic Modifier used. On an attack it
  deals maximum Damage and the attacker picks where it strikes.
* Natural 100 is a Critical Failure: always fails.
* A Characteristic of 0 always fails.
* An attack's Hit Location is the To Hit roll with its digits reversed.

No Qt here, so it can be unit tested with a seeded random generator.
"""

import random
from dataclasses import dataclass
from typing import Optional

# Simplified hit locations (reversed roll), then sublocations
LOCATIONS = (
    (10, "Head"), (20, "Left Arm"), (30, "Right Arm"),
    (45, "Left Leg"), (60, "Right Leg"), (100, "Chest"),
)
SUBLOCATIONS = (
    (2, "Neck"), (4, "Mouth"), (6, "Nose"), (7, "Eyes"), (8, "Ear"), (10, "Forehead"),
    (12, "Hand"), (15, "Forearm"), (16, "Elbow"), (19, "Bicep"), (20, "Shoulder"),
    (22, "Hand"), (25, "Forearm"), (26, "Elbow"), (29, "Bicep"), (30, "Shoulder"),
    (32, "Foot"), (37, "Shin"), (38, "Knee"), (43, "Thigh"), (45, "Hip"),
    (47, "Foot"), (53, "Shin"), (54, "Knee"), (58, "Thigh"), (60, "Hip"),
    (65, "Pelvis"), (72, "Intestines"), (78, "Spine"), (84, "Stomach, Kidney, or Liver"),
    (89, "Heart"), (96, "Lungs"), (100, "Ribcage, no organ struck"),
)


@dataclass(frozen=True)
class TestResult:
    roll: int
    target: int
    success: bool
    degrees: int
    critical: Optional[str] = None  # "success", "failure" or None
    note: str = ""

    @property
    def outcome(self) -> str:
        if self.critical == "success":
            return "Critical Success"
        if self.critical == "failure":
            return "Critical Failure"
        return "Success" if self.success else "Failure"

    @property
    def degrees_text(self) -> str:
        kind = "Success" if self.success else "Failure"
        plural = "Degree" if self.degrees == 1 else "Degrees"
        return f"{self.degrees} {plural} of {kind}"


def roll_d100(rng: Optional[random.Random] = None) -> int:
    return (rng or random).randint(1, 100)


def resolve_test(roll: int, target: int, characteristic: Optional[int] = None) -> TestResult:
    """Outcome of a D100 roll against a modified target.

    ``characteristic`` is the Characteristic used (for a Critical Success's
    minimum Degrees, and the automatic failure at 0).
    """
    roll, target = int(roll), int(target)
    if characteristic is not None and int(characteristic) <= 0:
        return TestResult(roll, target, False, max(0, (roll - target) // 10),
                          note="A Characteristic of 0 automatically fails.")
    if roll == 1:
        minimum = max(0, int(characteristic or 0) // 10)
        degrees = max(minimum, (target - roll) // 10 if target >= roll else 0)
        return TestResult(roll, target, True, degrees, "success")
    if roll >= 100:
        return TestResult(roll, target, False, max(0, (roll - target) // 10), "failure")
    if roll <= target:
        return TestResult(roll, target, True, (target - roll) // 10)
    return TestResult(roll, target, False, (roll - target) // 10)


def hit_location(roll: int) -> tuple:
    """(location, sublocation, reversed roll) struck by a To Hit roll: its digits reversed."""
    roll = int(roll)
    reversed_roll = 100 if roll >= 100 else int(f"{roll:02d}"[::-1]) or 100
    location = next(name for top, name in LOCATIONS if reversed_roll <= top)
    sublocation = next(name for top, name in SUBLOCATIONS if reversed_roll <= top)
    return location, sublocation, reversed_roll
