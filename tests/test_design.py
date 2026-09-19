"""The design of experiments is deterministic and matches the committed design."""

import csv

import pytest

import create_surrogate_doe_design as doe


def read_design(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def committed():
    return {
        "train": read_design(doe.TRAINING_CSV),
        "valid": read_design(doe.VALIDATION_CSV),
        "all": read_design(doe.ALL_CASES_CSV),
    }


def as_tuple(row):
    return (
        row["case_name"],
        row["dataset_split"],
        round(float(row["water_height_m"]), 6),
        round(float(row["obstacle_height_m"]), 6),
        round(float(row["obstacle_front_x_m"]), 6),
    )


def test_counts(committed):
    assert len(committed["train"]) == 343
    assert len(committed["valid"]) == 60
    assert len(committed["all"]) == 403
    names = [row["case_name"] for row in committed["all"]]
    assert len(names) == len(set(names))


def test_training_grid_regenerates_exactly(committed):
    width = float(committed["train"][0]["obstacle_width_m"])
    rows = doe.create_training_rows(width)
    assert [as_tuple(r) for r in rows] == [as_tuple(r) for r in committed["train"]]


def test_validation_lhs_regenerates_exactly(committed):
    width = float(committed["valid"][0]["obstacle_width_m"])
    rows = doe.create_validation_rows(width)
    assert [as_tuple(r) for r in rows] == [as_tuple(r) for r in committed["valid"]]


def test_validation_cases_are_off_grid_and_in_range(committed):
    for row in committed["valid"]:
        H = float(row["water_height_m"])
        h = float(row["obstacle_height_m"])
        x = float(row["obstacle_front_x_m"])
        assert doe.WATER_HEIGHT_RANGE[0] <= H <= doe.WATER_HEIGHT_RANGE[1]
        assert doe.OBSTACLE_HEIGHT_RANGE[0] <= h <= doe.OBSTACLE_HEIGHT_RANGE[1]
        assert doe.OBSTACLE_FRONT_X_RANGE[0] <= x <= doe.OBSTACLE_FRONT_X_RANGE[1]
        assert not doe.is_too_close_to_training_grid(H, h, x)


def test_latin_hypercube_has_one_sample_per_stratum():
    import random

    values = doe.latin_hypercube_values(0.0, 1.0, 10, random.Random(0))
    strata = sorted(int(v * 10) for v in values)
    assert strata == list(range(10))
