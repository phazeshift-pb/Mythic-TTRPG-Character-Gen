import pytest

from src.models import throwing as t


def test_weightless_throw_is_strength_total_times_15():
    # STR 50 -> modifier 5, Mythic +2 -> 7 x 15
    assert t.throw_distance(50, "+2").meters == 105


@pytest.mark.parametrize(
    "total,expected",
    [(1, (0.1, 2)), (2, (0.1, 2)), (3, (0.1, 1)), (6, (0.2, 1)), (9, (0.5, 1)),
     (12, (1.0, 1)), (18, (5.0, 1)), (25, (10.0, 1)), (40, (10.0, 1))],
)
def test_weight_step_table(total, expected):
    assert t.weight_step(total) == expected


def test_weight_penalty_uses_whole_steps_without_float_error():
    assert t.weight_penalty(3, 0.3) == 3  # 0.3 / 0.1 is 2.999... in floats
    assert t.weight_penalty(5, 0.5) == 2  # two full 0.2 kg steps
    assert t.weight_penalty(1, 0.4) == 8


def test_frag_grenade_example():
    # STR 50 (mod 5), no Mythic: 0.4 kg costs 2 -> 5 x 13
    assert t.throw_distance(50, 0, 0.4).meters == 65


def test_degrees_of_failure_lower_the_multiplier():
    assert t.throw_distance(50, 0, 0, degrees_of_failure=3).meters == 5 * 12


def test_grips():
    assert t.throw_distance(50, 0, 0, grip="Aerodynamic").meters == 5 * 19
    assert t.throw_distance(50, 0, 0, grip="Partial").meters == 5 * 13
    sloppy = t.throw_distance(50, 0, 0, grip="Sloppy")
    assert sloppy.meters == int(5 * 13 / 2) and sloppy.to_hit == -30


def test_negative_multiplier_throws_half_strength_modifier():
    # mod 6: every 0.2 kg -1, so 4 kg costs 20 -> multiplier -5
    result = t.throw_distance(60, 0, 4)
    assert result.multiplier == -5 and result.meters == 3


def test_multiplier_minus_ten_cannot_throw():
    assert not t.throw_distance(60, 0, 5).can_throw  # multiplier -10


def test_over_carry_weight_cannot_throw():
    result = t.throw_distance(50, 0, 30, carry_weight=25)
    assert not result.can_throw and "Carry Weight" in result.explanation


def test_tiny_range_cannot_throw():
    # mod 1: half modifier is 0.5 m (allowed), Sloppy halves it under 0.5 m
    assert t.throw_distance(10, 0, 1).meters == 0.5
    assert not t.throw_distance(10, 0, 1, grip="Sloppy").can_throw


def test_zero_strength_cannot_throw():
    assert not t.throw_distance(5, 0).can_throw


def test_range_text():
    assert t.throw_distance(50, 0).range_text() == "75 m"
    assert t.throw_distance(5, 0).range_text() == "Can't throw"
