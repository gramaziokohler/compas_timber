import pytest

from compas.data import json_dumps
from compas.data import json_loads

from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Vector
from compas.geometry import Transformation

from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.fabrication import Lap
from compas_timber.fabrication import OrientationType

from compas_timber.fabrication import LapProxy


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-2, relative=1e-2)


def test_lap_for_pocket_from_frame(tol):
    centerline = Line(
        Point(x=30396.1444398, y=-3257.66821289, z=73.5839565671),
        Point(x=34824.6096086, y=-3257.66821289, z=73.5839565671),
    )
    cross_section = [60, 120]
    beam = Beam.from_centerline(centerline, cross_section[0], cross_section[1])

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
    assert instance.machining_limits.limits == {
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
        Point(x=31941.779032189967, y=-3247.6682128899993, z=133.58495656710002),
        Point(x=31941.779032189967, y=-3247.6682128899993, z=13.582956567099998),
        Point(x=31808.42492581622, y=-3247.6682128899993, z=13.582956567099998),
        Point(x=31808.42492581622, y=-3247.6682128899993, z=133.58495656710002),
        Point(x=31941.779032189967, y=-3227.66821289, z=133.58495656710002),
        Point(x=31941.779032189967, y=-3227.66821289, z=13.582956567099998),
        Point(x=31808.42492581622, y=-3227.66821289, z=13.582956567099998),
        Point(x=31808.42492581622, y=-3227.66821289, z=133.58495656710002),
    ]

    expected_faces = [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]

    # assert vertices
    assert len(mesh_vertices) == len(expected_vertices)
    for vertex, expected_vertex in zip(mesh_vertices, expected_vertices):
        for coord, expected_coord in zip(vertex, expected_vertex):
            assert tol.is_close(coord, expected_coord)
    # assert faces
    assert len(mesh_faces) == len(expected_faces)
    for face, expected_face in zip(mesh_faces, expected_faces):
        assert face == expected_face


def test_lap_from_polyhedron(tol):
    centerline = Line(Point(x=598.9718391480744, y=442.07491356492113, z=-43.147538325873505), Point(x=439.346903483214, y=-335.92694125538884, z=69.2873648757245))
    cross_cection = [60, 60]
    z_vector = Vector(x=-0.379, y=0.208, z=0.902)
    beam = Beam.from_centerline(centerline, cross_cection[0], cross_cection[1], z_vector)

    polyhedron = Polyhedron(
        vertices=(
            Point(x=538.7940634854756, y=-30.0, z=17.375355587655925),
            Point(x=560.2327136921036, y=-30.0, z=-30.0),
            Point(x=545.7550689114237, y=30.0, z=20.525401820812363),
            Point(x=568.6192015970676, y=30.0, z=-30.0),
            Point(x=490.65016682732494, y=30.0, z=-4.4110805717187915),
            Point(x=502.22985601347585, y=30.0, z=-30.0),
            Point(x=483.6891614013768, y=-30.0, z=-7.561126804875222),
            Point(x=493.8433681085121, y=-30.0, z=-30.0),
        ),
        faces=[[1, 7, 5, 3], [0, 2, 4, 6], [1, 3, 2, 0], [3, 5, 4, 2], [5, 7, 6, 4], [7, 1, 0, 6]],
    )

    # Lap instance
    instance = Lap.from_volume_and_beam(polyhedron, beam, ref_side_index=0)

    # attribute assertions
    assert instance.orientation == "start"
    assert tol.is_close(instance.start_x, 414.510)
    assert tol.is_close(instance.start_y, 0.0)
    assert tol.is_close(instance.angle, 97.420)
    assert tol.is_close(instance.inclination, 102.009)
    assert tol.is_close(instance.slope, -1.552)
    assert tol.is_close(instance.length, 60.0)
    assert tol.is_close(instance.width, 60.0)
    assert tol.is_close(instance.depth, 21.843)
    assert instance.lead_angle_parallel
    assert instance.lead_inclination_parallel
    assert tol.is_close(instance.lead_angle, 90.0)
    assert tol.is_close(instance.lead_inclination, 90.0)
    assert instance.machining_limits.limits == {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }
    assert instance.ref_side_index == 0

    # volume from Lap instance
    polyhedron_volume = instance.volume_from_params_and_beam(beam)
    polyhedron_vertices, polyhedron_faces = polyhedron_volume.to_vertices_and_faces()

    # expected vertices and faces
    expected_vertices = [
        Point(x=545.7518711352025, y=29.98333920635866, z=20.52784609054484),
        Point(x=490.6469688626071, y=29.984565652479933, z=-4.408635885446827),
        Point(x=483.7033000113646, y=-30.015262730668805, z=-7.599938477900096),
        Point(x=538.80820228396, y=-30.016489176790078, z=17.33654349809157),
        Point(x=554.9647476420856, y=29.999999999999886, z=0.16913431102190285),
        Point(x=499.18166059019865, y=29.999999999999886, z=-23.268687779043713),
        Point(x=486.8693268123292, y=-30.009537209529466, z=-14.596257931322373),
        Point(x=542.6524138642161, y=-30.009537209529466, z=8.841564158743273),
    ]

    expected_faces = [[0, 1, 2, 3], [7, 6, 5, 4], [4, 5, 1, 0], [5, 6, 2, 1], [6, 7, 3, 2], [7, 4, 0, 3]]

    # assert vertices
    assert len(polyhedron_vertices) == len(expected_vertices)
    for vertex, expected_vertex in zip(polyhedron_vertices, expected_vertices):
        for coord, expected_coord in zip(vertex, expected_vertex):
            assert tol.is_close(coord, expected_coord)
    # assert faces
    assert len(polyhedron_faces) == len(expected_faces)
    for face, expected_face in zip(polyhedron_faces, expected_faces):
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
    assert copied_instance.machining_limits.limits == instance.machining_limits.limits
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

    params = instance.params.header_attributes
    params.update(instance.params.as_dict())

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


def test_lap_scaled():
    machining_limits = {
        "FaceLimitedBack": False,
        "FaceLimitedStart": True,
        "FaceLimitedBottom": True,
        "FaceLimitedTop": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
    }

    instance = Lap(
        OrientationType.END,
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

    scaled_instance = instance.scaled(2.0)

    assert scaled_instance.orientation == instance.orientation
    assert scaled_instance.start_x == instance.start_x * 2.0
    assert scaled_instance.start_y == instance.start_y * 2.0
    assert scaled_instance.angle == instance.angle
    assert scaled_instance.inclination == instance.inclination
    assert scaled_instance.slope == instance.slope
    assert scaled_instance.length == instance.length * 2.0
    assert scaled_instance.width == instance.width * 2.0
    assert scaled_instance.depth == instance.depth * 2.0
    assert scaled_instance.lead_angle == instance.lead_angle
    assert scaled_instance.lead_inclination == instance.lead_inclination
    assert scaled_instance.machining_limits.limits == instance.machining_limits.limits
    assert scaled_instance.ref_side_index == instance.ref_side_index


def test_lap_from_polyhedron_transforms_with_beam(tol):
    centerline = Line(Point(x=598.9718391480744, y=442.07491356492113, z=-43.147538325873505), Point(x=439.346903483214, y=-335.92694125538884, z=69.2873648757245))
    cross_section = [60, 60]
    z_vector = Vector(x=-0.379, y=0.208, z=0.902)
    beam_a = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)
    beam_b = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    polyhedron = Polyhedron(
        vertices=(
            Point(x=538.7940634854756, y=-30.0, z=17.375355587655925),
            Point(x=560.2327136921036, y=-30.0, z=-30.0),
            Point(x=545.7550689114237, y=30.0, z=20.525401820812363),
            Point(x=568.6192015970676, y=30.0, z=-30.0),
            Point(x=490.65016682732494, y=30.0, z=-4.4110805717187915),
            Point(x=502.22985601347585, y=30.0, z=-30.0),
            Point(x=483.6891614013768, y=-30.0, z=-7.561126804875222),
            Point(x=493.8433681085121, y=-30.0, z=-30.0),
        ),
        faces=[[1, 7, 5, 3], [0, 2, 4, 6], [1, 3, 2, 0], [3, 5, 4, 2], [5, 7, 6, 4], [7, 1, 0, 6]],
    )

    # Lap instances
    instance_a = Lap.from_volume_and_beam(polyhedron, beam_a, ref_side_index=0)
    instance_b = Lap.from_volume_and_beam(polyhedron, beam_b, ref_side_index=0)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # properties should be the same after transformation
    assert tol.is_close(instance_a.start_x, instance_b.start_x)
    assert tol.is_close(instance_a.start_y, instance_b.start_y)
    assert tol.is_close(instance_a.angle, instance_b.angle)
    assert tol.is_close(instance_a.inclination, instance_b.inclination)
    assert tol.is_close(instance_a.slope, instance_b.slope)
    assert tol.is_close(instance_a.length, instance_b.length)
    assert tol.is_close(instance_a.width, instance_b.width)
    assert tol.is_close(instance_a.depth, instance_b.depth)
    assert tol.is_close(instance_a.lead_angle, instance_b.lead_angle)
    assert tol.is_close(instance_a.lead_inclination, instance_b.lead_inclination)
    assert tol.is_close(instance_a.ref_side_index, instance_b.ref_side_index)

    # volumes should transform correctly
    volume_a = instance_a.volume_from_params_and_beam(beam_a)
    volume_b = instance_b.volume_from_params_and_beam(beam_b)

    vertices_a, faces_a = volume_a.to_vertices_and_faces()
    vertices_b, faces_b = volume_b.to_vertices_and_faces()

    assert len(vertices_a) == len(vertices_b)
    for vertex_a, vertex_b in zip(vertices_a, vertices_b):
        vertex_a.transform(transformation)
        assert tol.is_allclose(vertex_a, vertex_b)


def test_lap_proxy_transforms_with_beam(tol):
    centerline = Line(Point(x=598.9718391480744, y=442.07491356492113, z=-43.147538325873505), Point(x=439.346903483214, y=-335.92694125538884, z=69.2873648757245))
    cross_section = [60, 60]
    z_vector = Vector(x=-0.379, y=0.208, z=0.902)
    beam_a = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)
    beam_b = Beam.from_centerline(centerline, cross_section[0], cross_section[1], z_vector)

    polyhedron = Polyhedron(
        vertices=(
            Point(x=538.7940634854756, y=-30.0, z=17.375355587655925),
            Point(x=560.2327136921036, y=-30.0, z=-30.0),
            Point(x=545.7550689114237, y=30.0, z=20.525401820812363),
            Point(x=568.6192015970676, y=30.0, z=-30.0),
            Point(x=490.65016682732494, y=30.0, z=-4.4110805717187915),
            Point(x=502.22985601347585, y=30.0, z=-30.0),
            Point(x=483.6891614013768, y=-30.0, z=-7.561126804875222),
            Point(x=493.8433681085121, y=-30.0, z=-30.0),
        ),
        faces=[[1, 7, 5, 3], [0, 2, 4, 6], [1, 3, 2, 0], [3, 5, 4, 2], [5, 7, 6, 4], [7, 1, 0, 6]],
    )

    # LapProxy instances
    instance_a = LapProxy(polyhedron, beam_a, ref_side_index=0)
    instance_b = LapProxy(polyhedron, beam_b, ref_side_index=0)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # unproxify to get the actual Lap instances
    lap_a = instance_a.unproxified()
    lap_b = instance_b.unproxified()

    # properties should be the same after transformation
    assert tol.is_close(lap_a.start_x, lap_b.start_x)
    assert tol.is_close(lap_a.start_y, lap_b.start_y)
    assert tol.is_close(lap_a.angle, lap_b.angle)
    assert tol.is_close(lap_a.inclination, lap_b.inclination)
    assert tol.is_close(lap_a.slope, lap_b.slope)
    assert tol.is_close(lap_a.length, lap_b.length)
    assert tol.is_close(lap_a.width, lap_b.width)
    assert tol.is_close(lap_a.depth, lap_b.depth)
    assert tol.is_close(lap_a.lead_angle, lap_b.lead_angle)
    assert tol.is_close(lap_a.lead_inclination, lap_b.lead_inclination)
    assert tol.is_close(lap_a.ref_side_index, lap_b.ref_side_index)

    # volumes should transform correctly
    volume_a = lap_a.volume_from_params_and_beam(beam_a)
    volume_b = lap_b.volume_from_params_and_beam(beam_b)

    vertices_a, faces_a = volume_a.to_vertices_and_faces()
    vertices_b, faces_b = volume_b.to_vertices_and_faces()

    assert len(vertices_a) == len(vertices_b)
    for vertex_a, vertex_b in zip(vertices_a, vertices_b):
        vertex_a.transform(transformation)
        assert tol.is_allclose(vertex_a, vertex_b)
