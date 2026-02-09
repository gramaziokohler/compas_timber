import pytest

from compas.data import json_dumps
from compas.data import json_loads

from compas.geometry import Point
from compas.datastructures import Mesh
from compas.geometry import Polyhedron
from compas.geometry import Line
from compas.geometry import Vector
from compas.geometry import Frame
from compas.geometry import Transformation

from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.fabrication import Pocket
from compas_timber.fabrication import MachiningLimits
from compas_timber.connections import LapJoint

from compas_timber.fabrication import PocketProxy


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-2, relative=1e-2)


@pytest.fixture
def neg_vol():
    return Polyhedron(
        vertices=[
            Point(761.913, 30.000, -30.000),
            Point(733.833, 30.000, 20.356),
            Point(789.877, -30.000, -30.000),
            Point(765.028, -30.000, 14.561),
            Point(715.705, -30.000, -30.000),
            Point(697.185, -30.000, 3.214),
            Point(687.741, 30.000, -30.000),
            Point(665.989, 30.000, 9.008),
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
    instance = Pocket.from_volume_and_element(neg_vol, beam, ref_side_index=2)

    # attribute assertions
    assert tol.is_close(instance.start_x, 536.945)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.start_depth, 24.881)
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
    assert instance.machining_limits.limits == {
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
    instance = Pocket.from_volume_and_element(mesh_neg_vol, beam, ref_side_index=2)

    # attribute assertions
    assert tol.is_close(instance.start_x, 536.945)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.start_depth, 24.881)
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
    assert instance.machining_limits.limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == 2

    # volume from Lap instance
    pocket_volume = instance.volume_from_params_and_element(beam)
    vertices, faces = pocket_volume.to_vertices_and_faces()

    # expected vertices and faces
    expected_vertices = [
        Point(x=697.184, y=-30.000, z=3.213),
        Point(x=765.055, y=-29.990, z=14.507),
        Point(x=733.860, y=30.010, z=20.302),
        Point(x=665.988, y=30.000, z=9.008),
        Point(x=710.308, y=-30.009, z=-20.314),
        Point(x=771.817, y=-29.994, z=2.385),
        Point(x=737.389, y=30.008, z=13.975),
        Point(x=675.880, y=29.993, z=-8.724),
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
    assert copied_instance.machining_limits.limits == instance.machining_limits.limits
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

    params = instance.params.as_dict()

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


def test_pocket_with_5_faces(beam):
    base_points = [
        Point(788.77675, -19.774441, 30),
        Point(828.859137, -19.246494, 30),
        Point(828.33119, 20.835894, 30),
        Point(788.248803, 20.307946, 30),
    ]
    tip_point = Point(808.55397, 0.530726, 7.24627)

    vertices = base_points + [tip_point]
    faces = [[0, 4, 1], [1, 4, 2], [2, 4, 3], [3, 4, 0], [0, 1, 2, 3]]

    volume = Mesh.from_vertices_and_faces(vertices, faces)
    try:
        Pocket.from_volume_and_element(volume, beam, ref_side_index=2)
    except Exception as e:
        assert isinstance(e, ValueError)
        assert "Volume must have 6 faces." in str(e)


def test_pocket_scaled():
    limits = MachiningLimits().limits

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
        machining_limits=limits,
        ref_side_index=0,
    )

    scaled_instance = instance.scaled(2.0)

    assert scaled_instance.start_x == instance.start_x * 2.0
    assert scaled_instance.start_y == instance.start_y * 2.0
    assert scaled_instance.start_depth == instance.start_depth * 2.0
    assert scaled_instance.angle == instance.angle
    assert scaled_instance.inclination == instance.inclination
    assert scaled_instance.slope == instance.slope
    assert scaled_instance.length == instance.length * 2.0
    assert scaled_instance.width == instance.width * 2.0
    assert scaled_instance.internal_angle == instance.internal_angle
    assert scaled_instance.tilt_ref_side == instance.tilt_ref_side
    assert scaled_instance.tilt_end_side == instance.tilt_end_side
    assert scaled_instance.tilt_opp_side == instance.tilt_opp_side
    assert scaled_instance.tilt_start_side == instance.tilt_start_side


def test_pocket_from_polyhedron_transforms_with_beam(tol, neg_vol):
    centerline = Line(Point(x=982.9951560400838, y=-479.2205162374722, z=-67.36803489442559), Point(x=492.1609174771529, y=376.21927273785184, z=97.87275211713762))
    cross_section = [60, 60]
    z_vector = Vector(x=0.400, y=0.165, z=-0.855)

    beam_a = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector=z_vector)
    beam_b = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector=z_vector)

    # Pocket instances
    instance_a = Pocket.from_volume_and_element(neg_vol, beam_a, ref_side_index=2)
    instance_b = Pocket.from_volume_and_element(neg_vol, beam_b, ref_side_index=2)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # properties should be the same after transformation
    assert tol.is_close(instance_a.start_x, instance_b.start_x)
    assert tol.is_close(instance_a.start_y, instance_b.start_y)
    assert tol.is_close(instance_a.start_depth, instance_b.start_depth)
    assert tol.is_close(instance_a.angle, instance_b.angle)
    assert tol.is_close(instance_a.inclination, instance_b.inclination)
    assert tol.is_close(instance_a.slope, instance_b.slope)
    assert tol.is_close(instance_a.length, instance_b.length)
    assert tol.is_close(instance_a.width, instance_b.width)
    assert tol.is_close(instance_a.internal_angle, instance_b.internal_angle)
    assert tol.is_close(instance_a.tilt_ref_side, instance_b.tilt_ref_side)
    assert tol.is_close(instance_a.tilt_end_side, instance_b.tilt_end_side)
    assert tol.is_close(instance_a.tilt_opp_side, instance_b.tilt_opp_side)
    assert tol.is_close(instance_a.tilt_start_side, instance_b.tilt_start_side)
    assert tol.is_close(instance_a.ref_side_index, instance_b.ref_side_index)

    # volumes should transform correctly
    volume_a = instance_a.volume_from_params_and_element(beam_a)
    volume_b = instance_b.volume_from_params_and_element(beam_b)

    volume_a.transform(transformation)

    vertices_a, faces_a = volume_a.to_vertices_and_faces()
    vertices_b, faces_b = volume_b.to_vertices_and_faces()

    assert len(vertices_a) == len(vertices_b)
    for vertex_a, vertex_b in zip(vertices_a, vertices_b):
        assert tol.is_allclose(vertex_a, vertex_b)


def test_pocket_proxy_transforms_with_beam(tol, neg_vol):
    centerline = Line(Point(x=982.9951560400838, y=-479.2205162374722, z=-67.36803489442559), Point(x=492.1609174771529, y=376.21927273785184, z=97.87275211713762))
    cross_section = [60, 60]
    z_vector = Vector(x=0.400, y=0.165, z=-0.855)

    beam_a = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector=z_vector)
    beam_b = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector=z_vector)

    # PocketProxy instances
    instance_a = PocketProxy(neg_vol, beam_a, ref_side_index=2)
    instance_b = PocketProxy(neg_vol, beam_b, ref_side_index=2)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # unproxify to get the actual Pocket instances
    pocket_a = instance_a.unproxified()
    pocket_b = instance_b.unproxified()

    # properties should be the same after transformation
    assert tol.is_close(pocket_a.start_x, pocket_b.start_x)
    assert tol.is_close(pocket_a.start_y, pocket_b.start_y)
    assert tol.is_close(pocket_a.start_depth, pocket_b.start_depth)
    assert tol.is_close(pocket_a.angle, pocket_b.angle)
    assert tol.is_close(pocket_a.inclination, pocket_b.inclination)
    assert tol.is_close(pocket_a.slope, pocket_b.slope)
    assert tol.is_close(pocket_a.length, pocket_b.length)
    assert tol.is_close(pocket_a.width, pocket_b.width)
    assert tol.is_close(pocket_a.internal_angle, pocket_b.internal_angle)
    assert tol.is_close(pocket_a.tilt_ref_side, pocket_b.tilt_ref_side)
    assert tol.is_close(pocket_a.tilt_end_side, pocket_b.tilt_end_side)
    assert tol.is_close(pocket_a.tilt_opp_side, pocket_b.tilt_opp_side)
    assert tol.is_close(pocket_a.tilt_start_side, pocket_b.tilt_start_side)
    assert tol.is_close(pocket_a.ref_side_index, pocket_b.ref_side_index)

    # volumes should transform correctly
    volume_a = pocket_a.volume_from_params_and_element(beam_a)
    volume_b = pocket_b.volume_from_params_and_element(beam_b)

    volume_a.transform(transformation)

    vertices_a, faces_a = volume_a.to_vertices_and_faces()
    vertices_b, faces_b = volume_b.to_vertices_and_faces()

    assert len(vertices_a) == len(vertices_b)
    for vertex_a, vertex_b in zip(vertices_a, vertices_b):
        assert tol.is_allclose(vertex_a, vertex_b)
