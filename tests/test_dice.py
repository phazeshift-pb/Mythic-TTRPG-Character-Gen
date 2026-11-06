import random

import pytest

from src.models import dice


@pytest.mark.parametrize("roll,target,success,degrees", [
    # Worked examples from Mythic 7.0 CU1's example of play
    (55, 15, False, 4),   # Jackal: needs 15, rolls 55 -> 4 Degrees of Failure
    (11, 15, True, 0),    # "a Success with 0 Degrees"
    (45, 80, True, 3),    # Echo: needs 80, rolls 45 -> 3 Degrees of Success
    (87, 55, False, 3),   # Demo: needs 55, rolls 87 -> 3 Degrees of Failure
    (35, 105, True, 7),   # needs 105, rolls 35 -> 7 Degrees of Success
    (65, 95, True, 3),    # after -10 for switching targets
    (14, 95, True, 8),
    (50, 50, True, 0),    # equal to the target succeeds
    (51, 50, False, 0),
])
def test_degrees(roll, target, success, degrees):
    result = dice.resolve_test(roll, target, characteristic=45)
    assert (result.success, result.degrees) == (success, degrees)


def test_natural_100_always_fails():
    result = dice.resolve_test(100, 105, characteristic=45)  # the book's [100] against 105
    assert not result.success and result.critical == "failure" and result.outcome == "Critical Failure"


def test_natural_1_always_succeeds_with_minimum_degrees():
    low = dice.resolve_test(1, -20, characteristic=57)
    assert low.success and low.critical == "success" and low.degrees == 5
    high = dice.resolve_test(1, 90, characteristic=57)
    assert high.degrees == 8  # normal Degrees when higher than the minimum


def test_zero_characteristic_fails():
    assert not dice.resolve_test(5, 40, characteristic=0).success


def test_degrees_text():
    assert dice.resolve_test(45, 80).degrees_text == "3 Degrees of Success"
    assert dice.resolve_test(61, 50).degrees_text == "1 Degree of Failure"


@pytest.mark.parametrize("roll,location,sublocation", [
    (35, "Right Leg", "Shin"),    # reversed 53
    (10, "Head", "Neck"),         # reversed 01
    (70, "Head", "Eyes"),         # reversed 07
    (19, "Chest", "Lungs"),       # reversed 91
    (99, "Chest", "Ribcage, no organ struck"),
])
def test_hit_location(roll, location, sublocation):
    assert dice.hit_location(roll)[:2] == (location, sublocation)


def test_roll_range():
    rng = random.Random(1)
    rolls = {dice.roll_d100(rng) for _ in range(2000)}
    assert min(rolls) == 1 and max(rolls) == 100
