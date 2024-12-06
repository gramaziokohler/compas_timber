import pytest

from compas.data import json_dumps
from compas.data import json_loads

from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Vector

from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber._fabrication import Lap


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_lap_for_pocket_from_frame(tol):
    centerline = Line(
        Point(x=30396.1444398, y=-3257.66821289, z=73.5839565671),
        Point(x=34824.6096086, y=-3257.66821289, z=73.5839565671),
    )
    cross_cection = [60, 120]
    beam = Beam.from_centerline(centerline, cross_cection[0], cross_cection[1])

    cutting_frame = Frame(
        point=Point(x=31108.527, y=-2416.770, z=123.584),
        xaxis=Vector(x=0.708, y=-0.706, z=0.000),
        yaxis=Vector(x=0.000, y=-0.000, z=-1.000),
    )
    lap_length = 80.0
    lap_depth = 20.0
    ref_side_index = 1

    # Lap instance
    instance = Lap.from_plane_and_beam(
        cutting_frame,
        beam,
        lap_length,
        lap_depth,
        is_pocket=True,
        ref_side_index=ref_side_index,
    )

    # attribute assertions
    assert instance.orientation == "end"
    assert tol.is_close(instance.start_x, 1545.323)
    assert tol.is_close(instance.angle, 90.0)
    assert tol.is_close(instance.inclination, 90.0)
    assert tol.is_close(instance.slope, 0.0)
    assert tol.is_close(instance.length, 133.325)
    assert tol.is_close(instance.width, 120.0)
    assert tol.is_close(instance.depth, 20.0)
    assert tol.is_close(instance.lead_angle, 90.0)
    assert tol.is_close(instance.lead_inclination, 90.0)
    assert instance.machining_limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == ref_side_index

    # volume from Lap instance
    mesh_volume = instance.volume_from_params_and_beam(beam)
    mesh_vertices, mesh_faces = mesh_volume.to_vertices_and_faces()

    # expected vertices and faces
    expected_vertices = [
        [31941.467663941679, -3247.6682128906177, 13.58295656705431],
        [31941.467663941679, -3247.6682128906177, 133.58495656705432],
        [31808.142267843792, -3247.6682128906177, 133.58495656705432],
        [31808.142267843792, -3247.6682128906177, 13.58295656705431],
        [31941.467663941679, -3227.667212890618, 13.58295656705431],
        [31941.467663941679, -3227.667212890618, 133.58495656705432],
        [31808.142267843792, -3227.667212890618, 133.58495656705432],
        [31808.142267843792, -3227.667212890618, 13.58295656705431],
    ]
    expected_faces = [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [4, 5, 1, 0],
        [5, 6, 2, 1],
        [6, 7, 3, 2],
        [7, 4, 0, 3],
    ]

    # assert vertices
    assert len(mesh_vertices) == len(expected_vertices)
    for vertex, expected_vertex in zip(mesh_vertices, expected_vertices):
        for coord, expected_coord in zip(vertex, expected_vertex):
            assert tol.is_close(coord, expected_coord)
    # assert faces
    assert len(mesh_faces) == len(expected_faces)
    for face, expected_face in zip(mesh_faces, expected_faces):
        assert face == expected_face


def test_lap_for_halflaps_from_plane(tol):
    centerline = Line(
        Point(x=32087.5161016, y=-4629.03501941, z=73.5839565671),
        Point(x=33194.4503091, y=-1833.71037612, z=73.5839565671),
    )
    cross_cection = [80, 100]
    beam = Beam.from_centerline(centerline, cross_cection[0], cross_cection[1])

    cutting_plane = Plane(point=Point(x=30396.144, y=-3287.668, z=13.584), normal=Vector(x=-0.000, y=-1.000, z=0.000))
    lap_length = 60.0
    lap_depth = 88.0
    ref_side_index = 2

    # Lap instance
    instance = Lap.from_plane_and_beam(
        cutting_plane, beam, lap_length, lap_depth, is_pocket=False, ref_side_index=ref_side_index
    )

    # attribute assertions
    assert instance.orientation == "start"
    assert tol.is_close(instance.start_x, 1458.549)
    assert tol.is_close(instance.angle, 68.397)
    assert tol.is_close(instance.inclination, 90.0)
    assert tol.is_close(instance.slope, 0.0)
    assert tol.is_close(instance.length, 60.0)
    assert tol.is_close(instance.width, 80.0)
    assert tol.is_close(instance.depth, 88.0)
    assert tol.is_close(instance.lead_angle, 90.0)
    assert tol.is_close(instance.lead_inclination, 90.0)
    assert instance.machining_limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == ref_side_index

    # volume from Lap instance
    mesh_volume = instance.volume_from_params_and_beam(beam)
    mesh_vertices, mesh_faces = mesh_volume.to_vertices_and_faces()

    # expected vertices and faces
    expected_vertices = [
        [32575.667318015712, -3287.6682128900229, 35.583956567057157],
        [32661.713622767158, -3287.6682128900229, 35.583956567057157],
        [32685.473314726958, -3227.6682128899961, 35.583956567057157],
        [32599.427009975512, -3227.6682128899961, 35.583956567057157],
        [32575.667318015712, -3287.6682128900229, 123.58495656705432],
        [32661.713622767158, -3287.6682128900229, 123.58495656705432],
        [32685.473314726958, -3227.6682128899961, 123.58495656705433],
        [32599.427009975512, -3227.6682128899961, 123.58495656705433],
    ]
    expected_faces = [
        [3, 2, 1, 0],
        [7, 6, 5, 4],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7],
    ]

    # assert vertices
    assert len(mesh_vertices) == len(expected_vertices)
    for vertex, expected_vertex in zip(mesh_vertices, expected_vertices):
        for coord, expected_coord in zip(vertex, expected_vertex):
            assert tol.is_close(coord, expected_coord)
    # assert faces
    assert len(mesh_faces) == len(expected_faces)
    for face, expected_face in zip(mesh_faces, expected_faces):
        assert face == expected_face


def test_lap_data():
    machining_limits = {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }

    instance = Lap(
        "end",
        2289.328,
        0.0,
        111.603,
        90.0,
        0.0,
        80.0,
        60.0,
        22.0,
        True,
        90.0,
        True,
        90.0,
        machining_limits,
        ref_side_index=0,
    )
    copied_instance = json_loads(json_dumps(instance))

    assert copied_instance.orientation == instance.orientation
    assert copied_instance.start_x == instance.start_x
    assert copied_instance.start_y == instance.start_y
    assert copied_instance.angle == instance.angle
    assert copied_instance.inclination == instance.inclination
    assert copied_instance.slope == instance.slope
    assert copied_instance.length == instance.length
    assert copied_instance.width == instance.width
    assert copied_instance.depth == instance.depth
    assert copied_instance.lead_angle == instance.lead_angle
    assert copied_instance.lead_inclination == instance.lead_inclination
    assert copied_instance.machining_limits == instance.machining_limits
    assert copied_instance.ref_side_index == instance.ref_side_index


def test_lap_params_obj():
    machining_limits = {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }

    instance = Lap(
        "end",
        2289.328,
        0.0,
        111.603,
        90.0,
        0.0,
        80.0,
        60.0,
        22.0,
        True,
        90.0,
        True,
        90.0,
        machining_limits,
        ref_side_index=0,
    )

    params = instance.params_dict

    assert params["Name"] == "Lap"
    assert params["Process"] == "yes"
    assert params["Priority"] == "0"
    assert params["ProcessID"] == "0"
    assert params["ReferencePlaneID"] == "1"

    assert params["Orientation"] == "end"
    assert params["StartX"] == "2289.328"
    assert params["StartY"] == "0.000"
    assert params["Angle"] == "111.603"
    assert params["Inclination"] == "90.000"
    assert params["Slope"] == "0.000"
    assert params["Length"] == "80.000"
    assert params["Width"] == "60.000"
    assert params["Depth"] == "22.000"
    assert params["LeadAngleParallel"] == "yes"
    assert params["LeadAngle"] == "90.000"
    assert params["LeadInclinationParallel"] == "yes"
    assert params["LeadInclination"] == "90.000"
    assert params["MachiningLimits"] == {
        "FaceLimitedBack": "no",
        "FaceLimitedStart": "yes",
        "FaceLimitedBottom": "yes",
        "FaceLimitedTop": "no",
        "FaceLimitedEnd": "yes",
        "FaceLimitedFront": "no",
    }
