"""Case generation reproduces the committed OpenFOAM template exactly."""

import pytest

import generate_surrogate_database_cases as gen

TEMPLATE = gen.BASE_SETUP
TEMPLATE_CASE = "surrGrid_H0292_obsH0048_x0292"


@pytest.fixture(scope="module")
def template_case():
    cases = {case.name: case for case in gen.read_design_csv(gen.DESIGN_CSV)}
    return cases[TEMPLATE_CASE]


def test_design_csv_has_all_cases():
    assert len(gen.read_design_csv(gen.DESIGN_CSV)) == 403


def test_template_case_is_complete():
    for rel in ["0.orig/U", "0.orig/alpha.water", "0.orig/p_rgh",
                "constant/g", "constant/transportProperties",
                "constant/turbulenceProperties",
                "system/blockMeshDict", "system/controlDict",
                "system/fvSchemes", "system/fvSolution", "system/setFieldsDict"]:
        assert (TEMPLATE / rel).is_file(), rel
    assert not (TEMPLATE / "constant" / "polyMesh").exists()


def test_generated_case_matches_template(tmp_path, template_case):
    case_dir = tmp_path / TEMPLATE_CASE
    gen.copy_base_setup(case_dir)
    gen.write_block_mesh_dict(case_dir, template_case)
    gen.write_set_fields_dict(case_dir, template_case)
    gen.update_control_dict(case_dir, template_case)

    for rel in ["system/blockMeshDict", "system/setFieldsDict", "system/controlDict"]:
        assert (case_dir / rel).read_text() == (TEMPLATE / rel).read_text(), rel
    assert (case_dir / "0").is_dir()


def test_block_mesh_places_the_obstacle(tmp_path, template_case):
    case_dir = tmp_path / "case"
    (case_dir / "system").mkdir(parents=True)
    gen.write_block_mesh_dict(case_dir, template_case)
    text = (case_dir / "system" / "blockMeshDict").read_text()
    x1 = template_case.obstacle_front_x
    x2 = x1 + template_case.obstacle_width
    assert f"({x1:.9f} {template_case.obstacle_height:.9f} 0.000000000)" in text
    assert f"({x2:.9f} 0.000000000 0.000000000)" in text


def test_invalid_obstacle_is_rejected(tmp_path, template_case):
    from dataclasses import replace

    (tmp_path / "system").mkdir()
    bad = replace(template_case, obstacle_front_x=0.56)
    with pytest.raises(ValueError):
        gen.write_block_mesh_dict(tmp_path, bad)


def test_cell_count_respects_minimum():
    assert gen.cell_count(0.3, 0.003, 4) == 100
    assert gen.cell_count(0.001, 0.003, 4) == 4


def test_replace_dictionary_entry():
    text = "endTime         1;\nwriteInterval   0.05;\nwriteInterval   0.1;\n"
    out = gen.replace_dictionary_entry(text, "writeInterval", "0.025", first_only=True)
    assert "writeInterval   0.025;" in out
    assert "writeInterval   0.1;" in out
    with pytest.raises(ValueError):
        gen.replace_dictionary_entry(text, "deltaT", "0.001")


def test_function_object_interval_only_touches_that_object():
    text = (TEMPLATE / "system" / "controlDict").read_text()
    out = gen.enforce_function_object_interval(text, "obstaclePressureAverage", 0.01)
    avg = out[out.index("obstaclePressureAverage"):out.index("obstaclePressureMaximum")]
    rest = out[out.index("obstaclePressureMaximum"):]
    assert "writeInterval   0.01;" in avg
    assert "writeInterval   0.005;" in rest
    assert "writeInterval   0.025;" in out[:out.index("functions")]
