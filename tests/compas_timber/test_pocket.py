import pytest

from compas.data import json_dumps
from compas.data import json_loads

from compas.geometry import Point
from compas.datastructures import Mesh
from compas.geometry import Polyhedron
from compas.geometry import Line
from compas.geometry import Vector

from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.fabrication import Pocket
from compas_timber.connections import LapJoint


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-2, relative=1e-2)


@pytest.fixture
def neg_vol():
    return Polyhedron(
        vertices=[
            Point(x=710.3028152648835, y=-30.0, z=-20.31135977362403),
            Point(x=696.2754193511339, y=-30.0, z=4.844320113187994),
            Point(x=675.8760155142505, y=30.000000000000007, z=-8.721476594856815),
            Point(x=665.080014670604, y=30.000000000000007, z=10.639261702571591),
            Point(x=737.3918650442374, y=29.999999999999993, z=13.973883380857407),
            Point(x=732.9235961723932, y=29.999999999999993, z=21.9869416904287),
            Point(x=771.8186647948703, y=-30.0, z=2.384000202090148),
            Point(x=764.1190008529229, y=-30.0, z=16.19200010104508),
        ],
        faces=[[1, 7, 5, 3], [0, 2, 4, 6], [1, 3, 2, 0], [3, 5, 4, 2], [5, 7, 6, 4], [7, 1, 0, 6]],
    )


@pytest.fixture
def beam():
    centerline = Line(Point(x=982.9951560400838, y=-479.2205162374722, z=-67.36803489442559), Point(x=492.1609174771529, y=376.21927273785184, z=97.87275211713762))
    cross_section = [60, 60]
    z_vector = Vector(x=0.400, y=0.165, z=-0.855)

    return Beam.from_centerline(
        centerline,
        cross_section[0],
        cross_section[1],
        z_vector=z_vector,
    )


@pytest.fixture
def lap_joint(beam):
    cross_centerline = Line(Point(x=250.0, y=0.0, z=0.0), Point(x=1250.0, y=0.0, z=0.0))
    cross_vector = Vector(x=0.000, y=0.000, z=1.000)

    cross_beam = Beam.from_centerline(cross_centerline, 60, 60, z_vector=cross_vector)
    return LapJoint(beam, cross_beam)


def test_pocket_from_polyhedron(tol, neg_vol, beam):
    assert isinstance(neg_vol, Polyhedron)

    # Pocket instance
    instance = Pocket.from_volume_and_beam(neg_vol, beam, ref_side_index=2)

    # attribute assertions
    assert tol.is_close(instance.start_x, 536.945)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.start_depth, 26.602)
    assert tol.is_close(instance.angle, 0.0)
    assert tol.is_close(instance.inclination, -5.180)
    assert tol.is_close(instance.slope, 13.900)
    assert tol.is_close(instance.length, 60.975)
    assert tol.is_close(instance.width, 61.796)
    assert tol.is_close(instance.internal_angle, 116.055)
    assert tol.is_close(instance.tilt_ref_side, 76.154)
    assert tol.is_close(instance.tilt_end_side, 79.739)
    assert tol.is_close(instance.tilt_opp_side, 103.846)
    assert tol.is_close(instance.tilt_start_side, 100.261)
    assert instance.machining_limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == 2


def test_pocket_from_mesh(tol, neg_vol, beam):
    mesh_neg_vol = neg_vol.to_mesh()
    assert isinstance(mesh_neg_vol, Mesh)

    # Pocket instance
    instance = Pocket.from_volume_and_beam(mesh_neg_vol, beam, ref_side_index=2)

    # attribute assertions
    assert tol.is_close(instance.start_x, 536.945)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.start_depth, 26.602)
    assert tol.is_close(instance.angle, 0.0)
    assert tol.is_close(instance.inclination, -5.180)
    assert tol.is_close(instance.slope, 13.900)
    assert tol.is_close(instance.length, 60.975)
    assert tol.is_close(instance.width, 61.796)
    assert tol.is_close(instance.internal_angle, 116.055)
    assert tol.is_close(instance.tilt_ref_side, 76.154)
    assert tol.is_close(instance.tilt_end_side, 79.739)
    assert tol.is_close(instance.tilt_opp_side, 103.846)
    assert tol.is_close(instance.tilt_start_side, 100.261)
    assert instance.machining_limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == 2

    # volume from Lap instance
    pocket_volume = instance.volume_from_params_and_beam(beam)
    vertices, faces = pocket_volume.to_vertices_and_faces()

    # expected vertices and faces
    expected_vertices = [
        Point(x=696.2742881997966, y=-30.000000174621015, z=4.844131893265533),
        Point(x=764.1456308023633, y=-29.989522557661914, z=16.137703690909316),
        Point(x=732.9502261218345, y=30.01047744233868, z=21.932645280293613),
        Point(x=665.0788835192681, y=29.99999982537958, z=10.639073482649781),
        Point(x=710.3079812186909, y=-30.009871217206715, z=-20.31459044052669),
        Point(x=771.8173018048114, y=-29.994918670507513, z=2.3844143516783376),
        Point(x=737.3891973807285, y=30.007355151272794, z=13.974736752592545),
        Point(x=675.8798767946081, y=29.992402604573595, z=-8.72426803961245),
    ]
    expected_faces = [[0, 1, 2, 3], [7, 6, 5, 4], [4, 5, 1, 0], [5, 6, 2, 1], [6, 7, 3, 2], [7, 4, 0, 3]]

    # assert vertices
    assert len(vertices) == len(expected_vertices)
    for vertex, expected_vertex in zip(vertices, expected_vertices):
        for coord, expected_coord in zip(vertex, expected_vertex):
            assert tol.is_close(coord, expected_coord)
    # assert faces
    assert len(faces) == len(expected_faces)
    for face, expected_face in zip(faces, expected_faces):
        assert face == expected_face


def test_pocket_from_lap_joint(tol, lap_joint):
    neg_vol_main, _ = lap_joint._create_negative_volumes()

    instance = Pocket.from_volume_and_beam(neg_vol_main, lap_joint.main_beam, ref_side_index=lap_joint.main_ref_side_index)
    # attribute assertions
    assert tol.is_close(instance.start_x, 536.945)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.start_depth, 26.602)
    assert tol.is_close(instance.angle, 0.0)
    assert tol.is_close(instance.inclination, -5.180)
    assert tol.is_close(instance.slope, 13.900)
    assert tol.is_close(instance.length, 60.975)
    assert tol.is_close(instance.width, 61.796)
    assert tol.is_close(instance.internal_angle, 116.055)
    assert tol.is_close(instance.tilt_ref_side, 76.154)
    assert tol.is_close(instance.tilt_end_side, 79.739)
    assert tol.is_close(instance.tilt_opp_side, 103.846)
    assert tol.is_close(instance.tilt_start_side, 100.261)
    assert instance.machining_limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == 2


def test_pocket_data():
    machining_limits = {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }

    instance = Pocket(
        2289.328,
        0.0,
        22.0,
        111.603,
        90.0,
        0.0,
        80.0,
        60.0,
        22.0,
        100.0,
        90.0,
        50.0,
        90.0,
        machining_limits,
        ref_side_index=0,
    )
    copied_instance = json_loads(json_dumps(instance))

    assert copied_instance.start_x == instance.start_x
    assert copied_instance.start_y == instance.start_y
    assert copied_instance.start_depth == instance.start_depth
    assert copied_instance.angle == instance.angle
    assert copied_instance.inclination == instance.inclination
    assert copied_instance.slope == instance.slope
    assert copied_instance.length == instance.length
    assert copied_instance.width == instance.width
    assert copied_instance.internal_angle == instance.internal_angle
    assert copied_instance.tilt_ref_side == instance.tilt_ref_side
    assert copied_instance.tilt_end_side == instance.tilt_end_side
    assert copied_instance.tilt_opp_side == instance.tilt_opp_side
    assert copied_instance.tilt_start_side == instance.tilt_start_side
    assert copied_instance.machining_limits == instance.machining_limits
    assert copied_instance.ref_side_index == instance.ref_side_index


def test_pocket_params_obj():
    machining_limits = {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }

    instance = Pocket(
        2289.328,
        0.0,
        22.0,
        111.603,
        90.0,
        0.0,
        80.0,
        60.0,
        22.0,
        100.0,
        90.0,
        50.0,
        90.0,
        machining_limits,
        ref_side_index=0,
    )

    params = instance.params_dict

    assert params["Name"] == "Pocket"
    assert params["Process"] == "yes"
    assert params["Priority"] == "0"
    assert params["ProcessID"] == "0"
    assert params["ReferencePlaneID"] == "1"

    assert params["StartX"] == "2289.328"
    assert params["StartY"] == "0.000"
    assert params["StartDepth"] == "22.000"
    assert params["Angle"] == "111.603"
    assert params["Inclination"] == "90.000"
    assert params["Slope"] == "0.000"
    assert params["Length"] == "80.000"
    assert params["Width"] == "60.000"
    assert params["InternalAngle"] == "22.000"
    assert params["TiltRefSide"] == "100.000"
    assert params["TiltEndSide"] == "90.000"
    assert params["TiltOppSide"] == "50.000"
    assert params["TiltStartSide"] == "90.000"
    assert params["MachiningLimits"] == {
        "FaceLimitedBack": "no",
        "FaceLimitedStart": "yes",
        "FaceLimitedBottom": "yes",
        "FaceLimitedTop": "no",
        "FaceLimitedEnd": "yes",
        "FaceLimitedFront": "no",
    }
