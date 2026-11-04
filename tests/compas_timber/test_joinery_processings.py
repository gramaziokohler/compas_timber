import math

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Point

from compas_timber.elements import Beam
from compas_timber.fabrication import DovetailMortise
from compas_timber.fabrication import DovetailTenon
from compas_timber.fabrication import Mortise
from compas_timber.fabrication import Tenon
from compas_timber.fabrication.dovetail import Dovetail
from compas_timber.fabrication.house import House
from compas_timber.fabrication.house import HouseMortise
from compas_timber.fabrication.japanese_tenon import JapaneseMortise
from compas_timber.fabrication.japanese_tenon import JapaneseTenon
from compas_timber.fabrication.scarf_joint import ScarfJoint
from compas_timber.fabrication.tyrolean_dovetail import Frosch
from compas_timber.fabrication.tyrolean_dovetail import Klingschrot
from compas_timber.fabrication.tyrolean_dovetail import TyroleanDovetail

LENGTH, WIDTH, HEIGHT = 1000.0, 100.0, 200.0
SQRT2 = math.sqrt(2.0)


def apply(processing):
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([processing])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    return beam, geometry


def removed(processing):
    return LENGTH * WIDTH * HEIGHT - apply(processing)[1].volume


def holds(processing, x, y, depth):
    """True if a point, in the coordinates of the processing's reference side, is material after processing."""
    beam, geometry = apply(processing)
    return geometry.contains(beam.ref_sides[processing.ref_side_index].to_world_coordinates(Point(x, y, -depth)))


def copy_with_json(processing):
    return json_loads(json_dumps(processing))


@pytest.mark.parametrize(
    "make",
    [
        lambda: make_scarf(num_drill_hole=2),
        lambda: make_dovetail(),
        lambda: make_tyrolean(frosch=Frosch(20.0, 10.0)),
        lambda: make_japanese(),
        lambda: make_japanese(JapaneseMortise),
    ],
)
def test_volume_does_not_depend_on_the_position_of_the_beam(make):
    beam = Beam(Frame([100.0, -200.0, 300.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]), LENGTH, WIDTH, HEIGHT)
    beam.add_features([make()])
    geometry = beam.compute_elementgeometry(include_features=True)
    assert not beam.debug_info
    assert LENGTH * WIDTH * HEIGHT - geometry.volume == pytest.approx(removed(make()))


# ==============================================================================
# House and HouseMortise
# ==============================================================================


def make_house(**kwargs):
    params = dict(orientation="start", start_x=100.0, start_y=50.0, start_depth=20.0, length=160.0, width=80.0, height=20.0, shape="square", shape_radius=5.0)
    params.update(kwargs)
    return House(**params)


def make_tenon():
    return Tenon(orientation="start", start_x=80.0, start_y=50.0, start_depth=50.0, length=100.0, width=40.0, height=40.0, shape="square", shape_radius=5.0)


def make_house_mortise(**kwargs):
    return HouseMortise(start_x=100.0, start_y=50.0, start_depth=0.0, length=100.0, width=60.0, depth=20.0, shape="square", shape_radius=5.0, **kwargs)


def make_mortise():
    return Mortise(start_x=100.0, start_y=50.0, start_depth=20.0, length=60.0, width=30.0, depth=40.0, shape="square", shape_radius=5.0)


def test_house_has_the_parameters_of_a_tenon_under_its_own_name():
    params = make_house().params
    assert params.header_attributes["Name"] == "House"
    assert params.as_dict() == {
        "Orientation": "start",
        "StartX": "100.000",
        "StartY": "50.000",
        "StartDepth": "20.000",
        "Angle": "90.000",
        "Inclination": "90.000",
        "Rotation": "90.000",
        "LengthLimitedTop": "yes",
        "LengthLimitedBottom": "yes",
        "Length": "160.000",
        "Width": "80.000",
        "Height": "20.000",
        "Shape": "square",
        "ShapeRadius": "5.000",
        "Chamfer": "no",
    }


def test_house_mortise_has_the_parameters_of_a_mortise_under_its_own_name():
    params = make_house_mortise().params
    assert params.header_attributes["Name"] == "HouseMortise"
    assert list(params.as_dict())[:3] == ["StartX", "StartY", "StartDepth"]
    assert params.as_dict()["Depth"] == "20.000"


@pytest.mark.parametrize("make, nested", [(make_house, Mortise()), (make_house_mortise, Tenon()), (make_house, make_house())])
def test_house_rejects_nested_processing_of_the_wrong_type(make, nested):
    with pytest.raises(ValueError):
        make().add_subprocessing(nested)


def test_house_rejects_second_nested_processing():
    house = make_house(subprocessings=[make_tenon()])
    with pytest.raises(ValueError):
        house.add_subprocessing(make_tenon())


@pytest.mark.parametrize("make, nested", [(make_house, make_tenon), (make_house_mortise, make_mortise)])
def test_house_scales_with_nested_processing(make, nested):
    processing = make(subprocessings=[nested()])
    scaled = processing.scaled(2.0)
    assert scaled.start_x == 200.0
    assert scaled.subprocessings[0].start_x == 2.0 * nested().start_x
    assert scaled.subprocessings[0].length == 2.0 * nested().length
    assert processing.start_x == 100.0
    assert processing.subprocessings[0].start_x == nested().start_x


@pytest.mark.parametrize("make, nested", [(make_house, make_tenon), (make_house_mortise, make_mortise)])
def test_house_json_round_trip(make, nested):
    restored = copy_with_json(make(subprocessings=[nested()]))
    assert type(restored) is type(make())
    assert restored.params.as_dict() == make().params.as_dict()
    assert restored.subprocessings[0].params.as_dict() == nested().params.as_dict()


def test_house_leaves_a_block_at_the_cut():
    assert removed(make_house()) == pytest.approx(100.0 * WIDTH * HEIGHT - 160.0 * 80.0 * 20.0)
    assert holds(make_house(), 90.0, 50.0, 100.0)
    assert not holds(make_house(), 70.0, 50.0, 100.0)


def test_house_at_the_end_of_the_beam():
    house = make_house(orientation="end", start_x=900.0)
    assert removed(house) == pytest.approx(100.0 * WIDTH * HEIGHT - 160.0 * 80.0 * 20.0)
    assert holds(house, 910.0, 50.0, 100.0)
    assert not holds(house, 50.0 + 880.0, 50.0, 100.0)


def test_house_with_nested_tenon_on_top_of_the_block():
    house = make_house(subprocessings=[make_tenon()])
    assert removed(house) == pytest.approx(100.0 * WIDTH * HEIGHT - 160.0 * 80.0 * 20.0 - 100.0 * 40.0 * 40.0)
    assert holds(house, 60.0, 50.0, 100.0)
    assert not holds(house, 30.0, 50.0, 100.0)


def test_house_with_nested_dovetail_tenon():
    nested = DovetailTenon(orientation="start", start_x=80.0, start_y=50.0, start_depth=50.0, length=100.0, width=30.0, height=28.0)
    beam, geometry = apply(make_house(subprocessings=[nested]))
    assert LENGTH * WIDTH * HEIGHT - geometry.volume < 100.0 * WIDTH * HEIGHT - 160.0 * 80.0 * 20.0


def test_house_mortise_alone():
    assert removed(make_house_mortise()) == pytest.approx(100.0 * 60.0 * 20.0)


def test_house_mortise_nested_mortise_starts_at_the_bottom_of_the_house():
    house = make_house_mortise(subprocessings=[make_mortise()])
    assert removed(house) == pytest.approx(100.0 * 60.0 * 20.0 + 60.0 * 30.0 * 40.0)
    assert not holds(house, 130.0, 50.0, 50.0)
    assert holds(house, 130.0, 50.0, 70.0)


def test_house_mortise_with_nested_dovetail_mortise():
    nested = DovetailMortise(start_x=100.0, start_y=50.0, start_depth=20.0, length=60.0, width=30.0, depth=28.0)
    assert removed(make_house_mortise(subprocessings=[nested])) > 100.0 * 60.0 * 20.0


# ==============================================================================
# JapaneseTenon and JapaneseMortise
# ==============================================================================


def make_japanese(cls=JapaneseTenon, **kwargs):
    params = dict(start_x=300.0, width_1=30.0, length_1=50.0, width_2=50.0, length_2=50.0, width_3=40.0, middle_plane=10.0, offset=60.0, use_lap=False)
    params.update(kwargs)
    return cls(**params)


def section_area(width, center_depth=130.0, middle_plane=10.0):
    radius = (width - middle_plane) / 2.0
    return width * center_depth + math.pi * radius**2 / 2.0 + middle_plane * radius


TENON_VOLUME = section_area(30.0) * 50.0 + (section_area(50.0) + 4.0 * section_area(45.0) + section_area(40.0)) / 6.0 * 50.0


def test_japanese_tenon_params():
    params = JapaneseTenon(orientation="end", start_x=1.0, start_y=2.0, cone_angle=3.0, use_lap=False).params
    assert params.header_attributes["Name"] == "JapaneseTenon"
    assert params.as_dict() == {
        "Orientation": "end",
        "StartX": "1.000",
        "StartY": "2.000",
        "Width1": "40.000",
        "Length1": "50.000",
        "Width2": "60.000",
        "Length2": "50.000",
        "Width3": "40.000",
        "ConeAngle": "3.000",
        "MiddlePlane": "0.000",
        "Offset": "30.000",
        "UseLap": "no",
        "LapOffset": "10.000",
        "LapDepth": "20.000",
    }
    assert JapaneseMortise().params.header_attributes["Name"] == "JapaneseMortise"


@pytest.mark.parametrize("cls", [JapaneseTenon, JapaneseMortise])
@pytest.mark.parametrize(
    "kwargs",
    [
        {"orientation": "side"},
        {"start_x": 100001.0},
        {"start_y": -50001.0},
        {"width_1": -1.0},
        {"length_2": 100001.0},
        {"cone_angle": 30.1},
        {"use_lap": "yes"},
    ],
)
def test_japanese_limits(cls, kwargs):
    with pytest.raises(ValueError):
        cls(**kwargs)


@pytest.mark.parametrize("cls", [JapaneseTenon, JapaneseMortise])
def test_japanese_scale_and_json(cls):
    scaled = make_japanese(cls, cone_angle=5.0).scaled(2.0)
    assert (scaled.start_x, scaled.width_1, scaled.offset, scaled.cone_angle) == (600.0, 60.0, 120.0, 5.0)
    restored = copy_with_json(make_japanese(cls, cone_angle=5.0))
    assert type(restored) is cls
    assert restored.params.as_dict() == make_japanese(cls, cone_angle=5.0).params.as_dict()


def test_japanese_tenon_volume_without_lap():
    assert removed(make_japanese()) == pytest.approx(300.0 * WIDTH * HEIGHT - TENON_VOLUME, abs=TENON_VOLUME * 1e-3)


def test_japanese_tenon_lap_is_cut_into_the_shoulder():
    with_lap = make_japanese(use_lap=True, lap_offset=10.0, lap_depth=20.0)
    assert removed(with_lap) - removed(make_japanese()) == pytest.approx(20.0 * 50.0 * WIDTH)
    assert not holds(with_lap, 310.0, 50.0, 195.0)
    assert holds(with_lap, 310.0, 50.0, 145.0)
    assert holds(with_lap, 330.0, 50.0, 195.0)


@pytest.mark.parametrize(
    "orientation, start_x, sign",
    [("start", 300.0, -1.0), ("end", 700.0, 1.0)],
)
def test_japanese_tenon_runs_away_from_the_part(orientation, start_x, sign):
    tenon = make_japanese(orientation=orientation, start_x=start_x, start_y=40.0)
    assert holds(tenon, start_x + sign * 25.0, 40.0, 100.0)  # neck
    assert not holds(tenon, start_x + sign * 25.0, 40.0 + 20.0, 100.0)  # next to the neck
    assert holds(tenon, start_x + sign * 55.0, 40.0 + 20.0, 100.0)  # head
    assert not holds(tenon, start_x + sign * 110.0, 40.0, 100.0)  # past the head
    assert holds(tenon, start_x - sign * 10.0, 90.0, 100.0)  # the part


def test_japanese_tenon_bottom_of_the_neck_is_at_the_offset():
    tenon = make_japanese(start_y=50.0)
    assert holds(tenon, 275.0, 50.0, HEIGHT - 60.0 - 1.0)
    assert not holds(tenon, 275.0, 50.0, HEIGHT - 60.0 + 1.0)


def test_japanese_head_goes_deeper_than_the_neck():
    tenon = make_japanese(start_y=50.0)
    assert holds(tenon, 300.0 - 55.0, 50.0, HEIGHT - 60.0 + 5.0)


def test_japanese_cone_angle_narrows_with_the_depth():
    tenon = make_japanese(start_y=50.0, cone_angle=2.0)
    assert holds(tenon, 275.0, 63.0, 10.0)
    assert not holds(tenon, 275.0, 63.0, 100.0)


def test_japanese_flanks_which_do_not_reach_the_middle_plane_fail():
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([make_japanese(cone_angle=10.0)])
    beam.compute_elementgeometry(include_features=True)
    assert beam.debug_info


def test_japanese_mortise_volume_without_lap():
    assert removed(make_japanese(JapaneseMortise)) == pytest.approx(300.0 * WIDTH * HEIGHT + TENON_VOLUME, abs=TENON_VOLUME * 1e-3)


def test_japanese_mortise_lap_stands_out_of_the_shoulder():
    with_lap = make_japanese(JapaneseMortise, use_lap=True, lap_offset=10.0, lap_depth=20.0)
    assert removed(make_japanese(JapaneseMortise)) - removed(with_lap) == pytest.approx(20.0 * 50.0 * WIDTH)
    assert holds(with_lap, 290.0, 50.0, 195.0)
    assert not holds(with_lap, 290.0, 50.0, 145.0)
    assert not holds(with_lap, 270.0, 50.0, 195.0)


@pytest.mark.parametrize("orientation, start_x, sign", [("start", 300.0, 1.0), ("end", 700.0, -1.0)])
def test_japanese_mortise_runs_into_the_part(orientation, start_x, sign):
    mortise = make_japanese(JapaneseMortise, orientation=orientation, start_x=start_x, start_y=40.0)
    assert not holds(mortise, start_x + sign * 25.0, 40.0, 100.0)  # neck
    assert holds(mortise, start_x + sign * 25.0, 40.0 + 20.0, 100.0)  # next to the neck
    assert not holds(mortise, start_x + sign * 55.0, 40.0 + 20.0, 100.0)  # head
    assert holds(mortise, start_x + sign * 110.0, 40.0, 100.0)  # past the head
    assert holds(mortise, start_x + sign * 25.0, 40.0, HEIGHT - 30.0)  # below the neck
    assert not holds(mortise, start_x - sign * 10.0, 40.0, 100.0)  # the trimmed end


def test_japanese_tenon_and_mortise_fit():
    tenon = make_japanese(start_x=600.0, use_lap=True)
    mortise = make_japanese(JapaneseMortise, orientation="end", start_x=500.0, use_lap=True)
    assert abs(removed(tenon) - (600.0 * WIDTH * HEIGHT - TENON_VOLUME + 20.0 * 50.0 * WIDTH)) < TENON_VOLUME * 1e-3
    assert abs(removed(mortise) - (500.0 * WIDTH * HEIGHT + TENON_VOLUME - 20.0 * 50.0 * WIDTH)) < TENON_VOLUME * 1e-3


# ==============================================================================
# ScarfJoint
# ==============================================================================


def make_scarf(**kwargs):
    # at 45 degrees the profile is (0, 20), (80, 100), (100, 80), (200, 180)
    params = dict(orientation="start", start_x=100.0, inclination=45.0, lap_length=100.0 * SQRT2, lap_depth=20.0 * SQRT2, length=200.0, depth_opp_side=20.0)
    params.update(kwargs)
    return ScarfJoint(**params)


SCARF_VOLUME = (100.0 * HEIGHT + 20400.0) * WIDTH


def test_scarf_joint_params():
    params = ScarfJoint(inclination=30.0, num_drill_hole=2).params
    assert params.header_attributes["Name"] == "ScarfJoint"
    assert params.as_dict() == {
        "Orientation": "start",
        "StartX": "0.000",
        "Inclination": "30.000",
        "LapLength": "100.000",
        "LapDepth": "20.000",
        "Length": "200.000",
        "DepthOppSide": "20.000",
        "ScarfShape": "refside",
        "NumDrillHole": "2",
        "DrillHoleDiam1": "20.000",
        "DrillHoleDiam2": "20.000",
    }
    assert "Inclination" not in ScarfJoint().params.as_dict()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"orientation": "side"},
        {"start_x": 100001.0},
        {"inclination": 90.1},
        {"inclination": -0.1},
        {"lap_length": -1.0},
        {"scarf_shape": "round"},
        {"num_drill_hole": 3},
        {"drill_hole_diam_1": 1000.1},
    ],
)
def test_scarf_joint_limits(kwargs):
    with pytest.raises(ValueError):
        ScarfJoint(**kwargs)


def test_scarf_joint_scale_and_json():
    scaled = make_scarf(num_drill_hole=2).scaled(2.0)
    assert (scaled.start_x, scaled.length, scaled.drill_hole_diam_2, scaled.inclination, scaled.num_drill_hole) == (200.0, 400.0, 40.0, 45.0, 2)
    restored = copy_with_json(make_scarf(num_drill_hole=2))
    assert restored.params.as_dict() == make_scarf(num_drill_hole=2).params.as_dict()


def test_scarf_joint_refside():
    assert removed(make_scarf()) == pytest.approx(SCARF_VOLUME)
    assert not holds(make_scarf(), 90.0, 50.0, 5.0)  # in front of start_x
    assert holds(make_scarf(), 110.0, 50.0, 5.0)  # the tip stays on the reference side
    assert not holds(make_scarf(), 110.0, 50.0, 190.0)
    assert holds(make_scarf(), 305.0, 50.0, 195.0)  # behind the end of the scarf


def test_scarf_joint_at_the_end_of_the_beam():
    scarf = make_scarf(orientation="end", start_x=900.0)
    assert removed(scarf) == pytest.approx(SCARF_VOLUME)
    assert holds(scarf, 890.0, 50.0, 5.0)
    assert not holds(scarf, 890.0, 50.0, 190.0)
    assert holds(scarf, 695.0, 50.0, 195.0)


def test_scarf_joint_on_another_reference_side():
    scarf = make_scarf(ref_side_index=2)
    assert removed(scarf) == pytest.approx(SCARF_VOLUME)
    assert holds(scarf, 110.0, 50.0, 5.0)
    assert not holds(scarf, 110.0, 50.0, 190.0)


def test_scarf_joint_baseside_ends_are_perpendicular_to_the_faces():
    scarf = make_scarf(scarf_shape="baseside")
    assert removed(scarf) == pytest.approx(SCARF_VOLUME)
    assert not holds(scarf, 105.0, 50.0, 5.0)
    assert holds(scarf, 125.0, 50.0, 5.0)
    assert holds(scarf, 295.0, 50.0, 195.0)


def test_scarf_joint_classic_is_symmetrical_whatever_the_lap_length_and_depth_opp_side():
    scarf = make_scarf(scarf_shape="classic", lap_length=1.0, depth_opp_side=1.0)
    assert removed(scarf) == pytest.approx((100.0 * HEIGHT + 20000.0) * WIDTH)


def test_scarf_joint_drill_holes_at_the_quarters():
    scarf = make_scarf(num_drill_hole=2, drill_hole_diam_1=20.0, drill_hole_diam_2=20.0)
    assert removed(scarf) == pytest.approx(SCARF_VOLUME + math.pi * 100.0 * (70.0 + 130.0), rel=1e-6)
    assert not holds(scarf, 150.0, 50.0, 10.0)
    assert not holds(scarf, 250.0, 50.0, 10.0)


def test_scarf_joint_first_drill_hole_has_the_lower_x():
    scarf = make_scarf(orientation="end", start_x=900.0, num_drill_hole=2, drill_hole_diam_1=30.0, drill_hole_diam_2=10.0)
    assert not holds(scarf, 750.0 + 12.0, 50.0, 10.0)
    assert holds(scarf, 850.0 + 12.0, 50.0, 10.0)


def test_scarf_joint_without_inclination_fails():
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([ScarfJoint()])
    beam.compute_elementgeometry(include_features=True)
    assert beam.debug_info


# ==============================================================================
# Dovetail
# ==============================================================================


def make_dovetail(**kwargs):
    params = dict(start_x=100.0, slope=45.0, length=100.0, start_depth=100.0, height_ref_side=30.0, height_opp_side=30.0, lap_exit="none", cut_off=True)
    params.update(kwargs)
    return Dovetail(**params)


END_VOLUME = 100.0 * WIDTH * HEIGHT
LAP_VOLUME = 100.0 * 30.0 * HEIGHT
AMERICAN_TOP = 7350.0 * 100.0
AMERICAN_BOTTOM = 2450.0 * 70.0
AMERICAN_OVERLAP = 10.0**3 / 6.0  # the two faces meet in a corner of the tail, at 45 degrees
EUROPEAN_TOP = (7350.0 + 225.0) * 100.0
EUROPEAN_BOTTOM = (2450.0 - 1225.0) * 70.0


def test_dovetail_params():
    params = Dovetail(slope=10.0, cut_off=True).params
    assert params.header_attributes["Name"] == "Dovetail"
    assert params.as_dict() == {
        "Orientation": "start",
        "CutOff": "yes",
        "StartX": "0.000",
        "StartY": "30.000",
        "StartDepth": "50.000",
        "Slope": "10.000",
        "Length": "150.000",
        "RebateLength": "10.000",
        "HeightRefSide": "60.000",
        "HeightOppSide": "30.000",
        "LapPosition": "refedge",
        "LapExit": "mitre",
        "Shape": "european",
        "ProcessSide": "both",
    }
    assert "Slope" not in Dovetail().params.as_dict()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"orientation": "side"},
        {"cut_off": "yes"},
        {"start_y": -1.0},
        {"start_depth": 50001.0},
        {"slope": 45.1},
        {"length": -1.0},
        {"lap_position": "left"},
        {"lap_exit": "round"},
        {"shape": "asian"},
        {"process_side": "none"},
    ],
)
def test_dovetail_limits(kwargs):
    with pytest.raises(ValueError):
        Dovetail(**kwargs)


def test_dovetail_scale_and_json():
    scaled = make_dovetail().scaled(2.0)
    assert (scaled.start_x, scaled.length, scaled.height_opp_side, scaled.slope) == (200.0, 200.0, 60.0, 45.0)
    assert copy_with_json(make_dovetail()).params.as_dict() == make_dovetail().params.as_dict()


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"shape": "american"}, END_VOLUME + LAP_VOLUME + AMERICAN_TOP + AMERICAN_BOTTOM - AMERICAN_OVERLAP),
        ({"shape": "european"}, END_VOLUME + LAP_VOLUME + EUROPEAN_TOP + EUROPEAN_BOTTOM),
        ({"shape": "european", "cut_off": False}, LAP_VOLUME + EUROPEAN_TOP + EUROPEAN_BOTTOM),
        ({"shape": "american", "process_side": "refside"}, END_VOLUME + LAP_VOLUME + AMERICAN_TOP),
        ({"shape": "american", "process_side": "oppside"}, END_VOLUME + LAP_VOLUME + AMERICAN_BOTTOM),
        ({"shape": "american", "lap_exit": "mitre"}, END_VOLUME + LAP_VOLUME + 30.0 * 30.0 / 2.0 * HEIGHT + AMERICAN_TOP + AMERICAN_BOTTOM - AMERICAN_OVERLAP),
        ({"shape": "american", "lap_exit": "rebate", "rebate_length": 10.0}, END_VOLUME + LAP_VOLUME + 10.0 * 30.0 * HEIGHT + AMERICAN_TOP + AMERICAN_BOTTOM - AMERICAN_OVERLAP),
        ({"shape": "european", "lap_position": "oppedge"}, END_VOLUME + LAP_VOLUME + EUROPEAN_TOP + EUROPEAN_BOTTOM),
        ({"shape": "european", "orientation": "end", "start_x": 900.0}, END_VOLUME + LAP_VOLUME + EUROPEAN_TOP + EUROPEAN_BOTTOM),
    ],
)
def test_dovetail_volume(kwargs, expected):
    assert removed(make_dovetail(**kwargs)) == pytest.approx(expected)


@pytest.mark.parametrize("position, tail_y, lap_y", [("refedge", 35.0, 85.0), ("oppedge", 65.0, 15.0)])
@pytest.mark.parametrize("orientation, start_x, sign", [("start", 100.0, 1.0), ("end", 900.0, -1.0)])
def test_dovetail_tail_and_lap_are_on_the_correct_side(position, tail_y, lap_y, orientation, start_x, sign):
    dovetail = make_dovetail(lap_position=position, orientation=orientation, start_x=start_x)
    assert holds(dovetail, start_x + sign * 50.0, tail_y, 130.0)
    assert not holds(dovetail, start_x + sign * 50.0, lap_y, 130.0)
    assert holds(dovetail, start_x + sign * 110.0, lap_y, 130.0)
    assert not holds(dovetail, start_x - sign * 10.0, tail_y, 130.0)


def test_dovetail_upper_face_falls_towards_the_outer_edge():
    dovetail = make_dovetail(shape="american")
    assert holds(dovetail, 150.0, 65.0, 80.0)
    assert not holds(dovetail, 150.0, 5.0, 80.0)
    assert holds(dovetail, 150.0, 5.0, 140.0)


def test_dovetail_lower_face_falls_towards_the_end():
    dovetail = make_dovetail(shape="american")
    assert holds(dovetail, 110.0, 35.0, 190.0)
    assert not holds(dovetail, 190.0, 35.0, 190.0)


def test_dovetail_european_hooks():
    dovetail = make_dovetail(shape="european")
    assert not holds(dovetail, 150.0, 69.0, 80.0)  # behind the upper hook
    assert holds(dovetail, 150.0, 60.0, 90.0)
    assert holds(dovetail, 195.0, 35.0, 170.0)  # the lower hook leaves a ridge at the shoulder
    assert not holds(dovetail, 160.0, 35.0, 195.0)  # in front of the lower hook


def test_dovetail_without_cut_off_keeps_the_end():
    assert holds(make_dovetail(cut_off=False), 50.0, 85.0, 100.0)
    assert not holds(make_dovetail(cut_off=True), 50.0, 35.0, 130.0)


def test_dovetail_without_slope_fails():
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([Dovetail()])
    beam.compute_elementgeometry(include_features=True)
    assert beam.debug_info


# ==============================================================================
# TyroleanDovetail
# ==============================================================================


def make_tyrolean(**kwargs):
    params = dict(start_x=100.0, angle=90.0, slope=10.0, length=80.0, start_depth=100.0, height=60.0, lap_exit="none", cut_off=True)
    params.update(kwargs)
    return TyroleanDovetail(**params)


TAN = math.tan(math.radians(10.0))
TYROLEAN_LAP = 80.0 * 30.0 * HEIGHT
TYROLEAN_FACE = 80.0 * 70.0 * (40.0 - 5.0 * TAN)  # the average of the depths of the four corners of the upper face


def test_tyrolean_dovetail_params():
    params = TyroleanDovetail(angle=80.0, slope=10.0, frosch=Frosch(20.0, 10.0)).params
    assert params.header_attributes["Name"] == "TyroleanDovetail"
    frosch = params.as_dict().pop("Frosch")
    assert isinstance(frosch, Frosch)
    expected = {
        "Orientation": "start",
        "CutOff": "no",
        "StartX": "0.000",
        "StartY": "30.000",
        "StartDepth": "50.000",
        "Angle": "80.000",
        "Slope": "10.000",
        "Length": "150.000",
        "RebateLength": "10.000",
        "Height": "60.000",
        "LapPosition": "refedge",
        "LapExit": "mitre",
        "Shape": "angular",
        "ProcessSide": "both",
    }
    assert TyroleanDovetail(angle=80.0, slope=10.0).params.as_dict() == expected
    assert list(params.as_dict())[:-1] == list(expected)
    assert "Angle" not in TyroleanDovetail().params.as_dict()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"orientation": "side"},
        {"cut_off": "no"},
        {"start_y": -1.0},
        {"angle": 0.0},
        {"angle": 180.0},
        {"slope": 46.0},
        {"height": -1.0},
        {"shape": "round"},
        {"frosch": Frosch(1.0, 1.0), "klingschrot": Klingschrot(1.0, 1.0)},
    ],
)
def test_tyrolean_dovetail_limits(kwargs):
    with pytest.raises(ValueError):
        TyroleanDovetail(**kwargs)


@pytest.mark.parametrize("cls", [Frosch, Klingschrot])
def test_lock_profile_limits(cls):
    with pytest.raises(ValueError):
        cls(-1.0, 1.0)
    with pytest.raises(ValueError):
        cls(1.0, 50001.0)


def test_tyrolean_dovetail_scale_and_json():
    scaled = make_tyrolean(frosch=Frosch(20.0, 10.0)).scaled(2.0)
    assert (scaled.start_x, scaled.length, scaled.frosch.width, scaled.frosch.depth, scaled.angle) == (200.0, 160.0, 40.0, 20.0, 90.0)
    restored = copy_with_json(make_tyrolean(klingschrot=Klingschrot(300.0, 80.0)))
    assert (restored.klingschrot.radius, restored.klingschrot.arc_length) == (300.0, 80.0)
    assert restored.frosch is None
    restored = copy_with_json(make_tyrolean(frosch=Frosch(20.0, 10.0)))
    assert (restored.frosch.width, restored.frosch.depth) == (20.0, 10.0)


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({}, END_VOLUME + TYROLEAN_LAP + 2.0 * TYROLEAN_FACE),
        ({"cut_off": False}, TYROLEAN_LAP + 2.0 * TYROLEAN_FACE),
        ({"process_side": "refside"}, END_VOLUME + TYROLEAN_LAP + TYROLEAN_FACE),
        ({"process_side": "oppside"}, END_VOLUME + TYROLEAN_LAP + TYROLEAN_FACE),
        ({"lap_exit": "mitre"}, END_VOLUME + TYROLEAN_LAP + 30.0 * 30.0 / 2.0 * HEIGHT + 2.0 * TYROLEAN_FACE),
        ({"lap_exit": "rebate"}, END_VOLUME + TYROLEAN_LAP + 10.0 * 30.0 * HEIGHT + 2.0 * TYROLEAN_FACE),
        ({"lap_position": "oppedge"}, END_VOLUME + TYROLEAN_LAP + 2.0 * TYROLEAN_FACE),
        ({"orientation": "end", "start_x": 900.0}, END_VOLUME + TYROLEAN_LAP + 2.0 * TYROLEAN_FACE),
        ({"shape": "straight"}, END_VOLUME + TYROLEAN_LAP + 2.0 * 80.0 * 70.0 * (40.0 - 40.0 * TAN)),
    ],
)
def test_tyrolean_dovetail_volume(kwargs, expected):
    assert removed(make_tyrolean(**kwargs)) == pytest.approx(expected)


@pytest.mark.parametrize("position", ["refedge", "oppedge"])
def test_tyrolean_dovetail_volume_with_angle(position):
    # the depth of the upper face at the corners of the parallelogram, from the corner of the shoulder and the lap
    angle = math.radians(60.0)
    along_edge = 80.0 / math.sin(angle)
    along_shoulder = 70.0 / math.sin(angle)
    average_depth = 40.0 + TAN * (along_shoulder - along_edge) / 2.0
    lap = along_edge * 30.0 * HEIGHT
    faces = 2.0 * along_edge * 70.0 * average_depth
    tyrolean = make_tyrolean(start_x=300.0, angle=60.0, lap_position=position, cut_off=False)
    assert removed(tyrolean) == pytest.approx(lap + faces)


def test_tyrolean_dovetail_start_x_is_on_the_reference_edge():
    # the tail leans towards the end by 70 * cot(60) = 40.4 at the far edge of the tail
    tyrolean = make_tyrolean(start_x=300.0, angle=60.0)
    assert holds(tyrolean, 301.0, 1.0, 100.0)
    assert not holds(tyrolean, 299.0, 1.0, 100.0)
    assert holds(tyrolean, 262.0, 69.0, 100.0)
    assert not holds(tyrolean, 258.0, 69.0, 100.0)


def test_tyrolean_dovetail_start_x_is_on_the_reference_edge_also_with_the_tail_on_the_opposite_edge():
    # the end line passes (300, 0), and the tail starts at y = 30
    tyrolean = make_tyrolean(start_x=300.0, angle=60.0, lap_position="oppedge")
    assert holds(tyrolean, 284.0, 32.0, 100.0)
    assert not holds(tyrolean, 280.0, 32.0, 100.0)
    assert not holds(tyrolean, 300.0, 15.0, 100.0)


@pytest.mark.parametrize("position, tail_y, lap_y", [("refedge", 35.0, 85.0), ("oppedge", 65.0, 15.0)])
@pytest.mark.parametrize("orientation, start_x, sign", [("start", 100.0, 1.0), ("end", 900.0, -1.0)])
def test_tyrolean_dovetail_tail_and_lap_are_on_the_correct_side(position, tail_y, lap_y, orientation, start_x, sign):
    tyrolean = make_tyrolean(lap_position=position, orientation=orientation, start_x=start_x)
    assert holds(tyrolean, start_x + sign * 40.0, tail_y, 100.0)
    assert not holds(tyrolean, start_x + sign * 40.0, lap_y, 100.0)
    assert holds(tyrolean, start_x + sign * 90.0, lap_y, 100.0)
    assert not holds(tyrolean, start_x - sign * 10.0, tail_y, 100.0)


@pytest.mark.parametrize("position, near_y, far_y", [("refedge", 1.0, 69.0), ("oppedge", 99.0, 31.0)])
def test_tyrolean_dovetail_faces_widen_towards_the_end_and_the_lap(position, near_y, far_y):
    tyrolean = make_tyrolean(lap_position=position)
    drop = 70.0 * TAN  # of the upper face across the tail
    length_drop = 80.0 * TAN
    assert holds(tyrolean, 179.0, far_y, 42.0)  # the corner of the shoulder and the lap, at 40
    assert not holds(tyrolean, 179.0, far_y, 38.0)
    assert holds(tyrolean, 179.0, near_y, 42.0 + drop)
    assert not holds(tyrolean, 179.0, near_y, 38.0 + drop)
    assert holds(tyrolean, 101.0, far_y, 42.0 - length_drop)
    assert not holds(tyrolean, 101.0, far_y, 36.0 - length_drop)


def test_tyrolean_dovetail_faces_are_symmetrical():
    tyrolean = make_tyrolean()
    assert holds(tyrolean, 179.0, 69.0, 158.0)
    assert not holds(tyrolean, 179.0, 69.0, 162.0)


def test_tyrolean_dovetail_frosch_bulge_stands_out_of_the_tail():
    frosch = Frosch(20.0, 10.0)
    assert holds(make_tyrolean(frosch=frosch), 105.0, 75.0, 100.0)
    assert not holds(make_tyrolean(), 105.0, 75.0, 100.0)
    assert not holds(make_tyrolean(frosch=frosch), 165.0, 75.0, 100.0)  # the bulge stops short of the shoulder
    assert not holds(make_tyrolean(frosch=frosch), 105.0, 85.0, 100.0)  # the bulge has a depth


def test_tyrolean_dovetail_frosch_pockets_are_in_the_corners_of_the_shoulder():
    frosch = Frosch(20.0, 10.0)
    tyrolean = make_tyrolean(frosch=frosch)
    assert not holds(tyrolean, 185.0, 5.0, 5.0)
    assert not holds(tyrolean, 185.0, 5.0, 195.0)
    assert holds(make_tyrolean(), 185.0, 5.0, 5.0)
    assert holds(tyrolean, 185.0, 5.0, 100.0)
    assert holds(tyrolean, 185.0, 60.0, 5.0)  # the pockets stop short of the lap
    assert holds(tyrolean, 195.0, 5.0, 5.0)  # the pockets have a depth


def test_tyrolean_dovetail_frosch_wider_than_the_tail_fails():
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([make_tyrolean(frosch=Frosch(75.0, 10.0))])
    beam.compute_elementgeometry(include_features=True)
    assert beam.debug_info


def test_tyrolean_dovetail_frosch_pocket_only_on_the_processed_side():
    tyrolean = make_tyrolean(frosch=Frosch(20.0, 10.0), process_side="refside")
    assert not holds(tyrolean, 185.0, 5.0, 5.0)
    assert holds(tyrolean, 185.0, 5.0, 195.0)


def test_tyrolean_dovetail_klingschrot_faces_stay_planar():
    assert removed(make_tyrolean(klingschrot=Klingschrot(300.0, 80.0))) == pytest.approx(END_VOLUME + TYROLEAN_LAP + 2.0 * TYROLEAN_FACE)


@pytest.mark.parametrize("kwargs", [{"angle": None}, {"slope": None}])
def test_tyrolean_dovetail_without_angle_or_slope_fails(kwargs):
    beam = Beam(Frame.worldXY(), LENGTH, WIDTH, HEIGHT)
    beam.add_features([make_tyrolean(**kwargs)])
    beam.compute_elementgeometry(include_features=True)
    assert beam.debug_info
