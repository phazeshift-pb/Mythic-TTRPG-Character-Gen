"""Throwing distance rules (Mythic 7.0 CU1, Improvised Weaponry > Throwing Objects).

Pure functions, no Qt, so the character sheet and tests share them.

Summary of the book's rule:

* Range = (Strength Modifier + Mythic Strength) x Multiplier, in Meters.
  The Multiplier starts at 15.
* Each Degree of Failure on the Warfare Melee Test lowers the Multiplier by 1.
* The object's weight lowers the Multiplier, at a rate set by
  Strength Modifier + Mythic Strength (WEIGHT_STEPS below).
* Grip: Partial -2, Sloppy -2 and half distance, Aerodynamic +4.
* If the Multiplier goes negative the object only goes half the Strength
  Modifier in Meters; at -10 or lower it can't be thrown.
* Heavier than Carry Weight, or a total range under half a Meter: can't be
  thrown. Round down to the nearest whole Meter.
"""

from dataclasses import dataclass
from typing import Any, Optional

from src.models.derived_stats import characteristic_modifier, mythic_value

BASE_MULTIPLIER = 15
CANT_THROW_MULTIPLIER = -10
MIN_RANGE_METERS = 0.5

# (highest Strength Modifier + Mythic Strength, kg per step, Multiplier lost per step)
WEIGHT_STEPS = (
    (2, 0.1, 2),
    (4, 0.1, 1),
    (6, 0.2, 1),
    (9, 0.5, 1),
    (12, 1.0, 1),
    (18, 5.0, 1),
    (25, 10.0, 1),
)

# name: (Multiplier change, halves distance, To Hit penalty, description)
GRIPS = {
    "Solid": (0, False, 0, "Solid grip, no Penalties."),
    "Slight": (0, False, -20, "Grip isn't the best: -20 To Hit."),
    "Partial": (-2, False, -20, "Grip is off: Multiplier -2, -20 To Hit."),
    "Sloppy": (-2, True, -30, "Weak grip: Multiplier -2, half distance, -30 To Hit."),
    "Aerodynamic": (4, False, 0, "Built to be thrown: Multiplier +4."),
}


@dataclass(frozen=True)
class ThrowResult:
    meters: Optional[float]  # None when the object can't be thrown
    multiplier: int
    to_hit: int
    explanation: str

    @property
    def can_throw(self) -> bool:
        return self.meters is not None

    def range_text(self) -> str:
        if self.meters is None:
            return "Can't throw"
        return f"{self.meters:g} m"


def throw_strength(strength: Any, mythic_strength: Any = 0) -> int:
    """Strength Modifier + Mythic Strength."""
    return characteristic_modifier(int(strength or 0)) + mythic_value(mythic_strength)


def weight_step(strength_total: int) -> tuple[float, int]:
    """(kg per step, Multiplier lost per step) for a Strength Modifier + Mythic total.

    The book's table stops at 25; higher totals keep the 10 kg step.
    """
    for highest, step_kg, per_step in WEIGHT_STEPS:
        if strength_total <= highest:
            return step_kg, per_step
    return WEIGHT_STEPS[-1][1], WEIGHT_STEPS[-1][2]


def weight_penalty(strength_total: int, weight_kg: float) -> int:
    """How much an object's weight lowers the Multiplier."""
    step_kg, per_step = weight_step(strength_total)
    # Whole grams avoid float trouble such as 0.3 / 0.1 == 2.999...
    grams = int(round(max(0.0, float(weight_kg)) * 1000))
    step_grams = int(round(step_kg * 1000))
    return (grams // step_grams) * per_step


def throw_distance(
    strength: Any,
    mythic_strength: Any = 0,
    weight_kg: float = 0.0,
    *,
    grip: str = "Solid",
    degrees_of_failure: int = 0,
    carry_weight: Optional[float] = None,
) -> ThrowResult:
    """How far a character can throw an object."""
    strength_modifier = characteristic_modifier(int(strength or 0))
    total = strength_modifier + mythic_value(mythic_strength)
    grip_change, grip_halves, to_hit, _ = GRIPS.get(grip, GRIPS["Solid"])
    weight = max(0.0, float(weight_kg or 0))

    if carry_weight is not None and weight > carry_weight:
        return ThrowResult(None, 0, to_hit, f"{weight:g} kg is over Carry Weight ({carry_weight:g} kg).")
    if total <= 0:
        return ThrowResult(None, 0, to_hit, "Strength Modifier + Mythic Strength is 0.")

    lost_to_weight = weight_penalty(total, weight)
    dof = max(0, int(degrees_of_failure or 0))
    multiplier = BASE_MULTIPLIER - lost_to_weight - dof + grip_change
    parts = [f"x{BASE_MULTIPLIER}"]
    if lost_to_weight:
        parts.append(f"-{lost_to_weight} weight")
    if dof:
        parts.append(f"-{dof} DoF")
    if grip_change:
        parts.append(f"{grip_change:+d} {grip} grip")
    working = " ".join(parts)

    if multiplier <= CANT_THROW_MULTIPLIER:
        return ThrowResult(None, multiplier, to_hit, f"Multiplier {multiplier} ({working}) is -10 or lower.")
    if multiplier <= 0:
        raw = strength_modifier / 2
        explanation = f"Multiplier {multiplier} ({working}): half Strength Modifier ({strength_modifier})"
    else:
        raw = total * multiplier
        explanation = f"{total} x {multiplier} ({working})"
    if grip_halves:
        raw /= 2
        explanation += ", halved for Sloppy grip"

    if raw < MIN_RANGE_METERS:
        return ThrowResult(None, multiplier, to_hit, explanation + ": under half a Meter.")
    meters = float(int(raw)) if raw >= 1 else MIN_RANGE_METERS
    return ThrowResult(meters, multiplier, to_hit, explanation)
