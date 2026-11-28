import pytest
import pytest_mock

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.tolerance import TOL
from compas_timber.connections import Joint
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fasteners import Fastener
from compas_timber.model import TimberModel
from compas_timber.structural import PlateStructuralElementSolver
from compas_timber.structural import SimpleBeamSegmentGenerator
from compas_timber.structural import SimpleJointConnectorGenerator
from compas_timber.structural import StructuralGraph
from compas_timber.structural import StructuralSurface
from compas_timber.structural import StructuralSurfaceLine
from compas_timber.structural import effective_centerline
from compas_timber.structural import _get_open_points
from compas_timber.structural import _get_plate_center_outline


def _plate(points, thickness=20.0):
    return Plate.from_outline_thickness(Polyline(points + [points[0]]), thickness)


@pytest.fixture
def l_corner_model():
    """A horizontal plate meeting a taller vertical plate along its end at x=1000."""
    model = TimberModel()
    plate_a = _plate([Point(0, 0, 0), Point(1000, 0, 0), Point(1000, 500, 0), Point(0, 500, 0)])
    plate_b = _plate([Point(1000, 0, 0), Point(1000, 0, 1000), Point(1000, 500, 1000), Point(1000, 500, 0)])
    model.add_element(plate_a)
    model.add_element(plate_b)
    model.connect_adjacent_plates()
    return model, plate_a, plate_b


def _solve(model):
    solver = PlateStructuralElementSolver()
    surfaces, joints = solver.add_structural_surfaces(model)
    lines = solver.add_joint_structural_lines(model, joints)
    return surfaces, lines


# =============================================================================
# StructuralSurface / StructuralSurfaceLine
# =============================================================================


def test_structural_surface_attributes():
    outline = Polyline([Point(0, 0, 0), Point(1, 0, 0), Point(1, 1, 0), Point(0, 0, 0)])
    surface = StructuralSurface(outline, Frame.worldXY(), 20.0, name="slab", material="C24")

    assert surface.name == "slab"
    # `name` belongs to Data, not to the free-form attributes
    assert surface.attributes == {"material": "C24"}


def test_structural_surface_line_attributes():
    line = StructuralSurfaceLine(Line(Point(0, 0, 0), Point(1, 0, 0)), line_type="hinge", stiffness=1.0)

    assert line.line_type == "hinge"
    assert line.attributes == {"stiffness": 1.0}


def test_structural_surface_parent_plate_guid(l_corner_model):
    model, plate_a, _ = l_corner_model
    _solve(model)

    surface = model.get_plate_structural_surfaces(plate_a)[0]

    assert surface.parent_plate is plate_a
    assert surface.parent_plate_guid == str(plate_a.guid)
    # the plate is referenced by guid, not embedded
    assert surface.__data__["parent_plate_guid"] == str(plate_a.guid)
    assert "parent_plate" not in surface.__data__


# =============================================================================
# Surface and connection generation
# =============================================================================


def test_surface_frame_normal_is_plate_normal(l_corner_model):
    model, plate_a, plate_b = l_corner_model
    _solve(model)

    normal_a = model.get_plate_structural_surfaces(plate_a)[0].frame.normal
    normal_b = model.get_plate_structural_surfaces(plate_b)[0].frame.normal

    assert TOL.is_close(abs(normal_a.dot(Vector.Zaxis())), 1.0)
    assert TOL.is_close(abs(normal_b.dot(Vector.Xaxis())), 1.0)


def test_connection_line_is_the_joined_edge(l_corner_model):
    model, plate_a, plate_b = l_corner_model
    _, lines = _solve(model)

    assert len(lines) == 2
    assert {line.parent_plate.guid for line in lines} == {plate_a.guid, plate_b.guid}

    # the joined edge runs along y at the end of plate_a, in the mid-plane of plate_b
    line = lines[0].line
    surface_b = model.get_plate_structural_surfaces(plate_b)[0]
    for point in (line.start, line.end):
        assert TOL.is_zero(Vector.from_start_end(surface_b.frame.point, point).dot(surface_b.frame.normal))
    assert TOL.is_close(abs(line.direction.dot(Vector.Yaxis())), 1.0)


def test_square_plate_is_stretched_to_its_joint():
    # plate_b is square, so its longest edge (along y) says nothing about where its joint is:
    # its bottom edge must still be stretched down to the mid-plane of plate_a
    model = TimberModel()
    plate_a = _plate([Point(0, 0, 0), Point(1000, 0, 0), Point(1000, 500, 0), Point(0, 500, 0)])
    plate_b = _plate([Point(1000, 0, 0), Point(1000, 500, 0), Point(1000, 500, 500), Point(1000, 0, 500)])
    model.add_element(plate_a)
    model.add_element(plate_b)
    model.connect_adjacent_plates()

    _, lines = _solve(model)

    surface_a = model.get_plate_structural_surfaces(plate_a)[0]
    surface_b = model.get_plate_structural_surfaces(plate_b)[0]
    bottom_z = min(point.z for point in surface_b.outline.points)
    assert TOL.is_close(bottom_z, surface_a.frame.point.z)
    assert len(lines) == 2


@pytest.fixture
def long_edge_l_model():
    """A floor and a wall meeting along their 3000 mm long edges at y=1000."""
    model = TimberModel()
    floor = _plate([Point(0, 0, 0), Point(3000, 0, 0), Point(3000, 1000, 0), Point(0, 1000, 0)])
    wall = _plate([Point(0, 1000, 0), Point(3000, 1000, 0), Point(3000, 1000, 1000), Point(0, 1000, 1000)])
    model.add_element(floor)
    model.add_element(wall)
    model.connect_adjacent_plates()
    return model, floor, wall


def test_plates_joined_along_their_long_edges_are_stretched(long_edge_l_model):
    # the joined edges are the long ones, so looking at the ends of the longest edge finds nothing:
    # the joint's segment indices say which edge to move
    model, floor, wall = long_edge_l_model
    _, lines = _solve(model)

    floor_surface = model.get_plate_structural_surfaces(floor)[0]
    wall_surface = model.get_plate_structural_surfaces(wall)[0]
    floor_mid_z = floor_surface.frame.point.z
    wall_mid_y = wall_surface.frame.point.y

    # the floor reaches the wall's mid-plane and the wall reaches the floor's, along the whole edge
    assert [TOL.is_close(point.y, wall_mid_y) for point in _get_open_points(floor_surface.outline)].count(True) == 2
    assert TOL.is_close(max(point.y for point in floor_surface.outline.points), wall_mid_y)
    assert TOL.is_close(min(point.z for point in wall_surface.outline.points), floor_mid_z)
    # the far edges stay where they were
    assert TOL.is_zero(min(point.y for point in floor_surface.outline.points))
    assert TOL.is_close(max(point.z for point in wall_surface.outline.points), 1000)
    # both surfaces stay flat
    for surface in (floor_surface, wall_surface):
        for point in surface.outline.points:
            assert TOL.is_zero(Vector.from_start_end(surface.frame.point, point).dot(surface.frame.normal))
    assert len(lines) == 2


def test_through_plate_of_a_t_joint_is_not_stretched():
    # a wall standing on the middle of a floor: the wall's edge goes down to the floor's mid-plane,
    # the floor has no edge at the joint and keeps its outline
    model = TimberModel()
    floor = _plate([Point(0, 0, 0), Point(3000, 0, 0), Point(3000, 1000, 0), Point(0, 1000, 0)])
    wall = _plate([Point(0, 500, 0), Point(3000, 500, 0), Point(3000, 500, 1000), Point(0, 500, 1000)])
    model.add_element(floor)
    model.add_element(wall)
    model.connect_adjacent_plates()

    before = [Point(*point) for point in _get_open_points(_get_plate_center_outline(floor))]
    _solve(model)

    floor_surface = model.get_plate_structural_surfaces(floor)[0]
    wall_surface = model.get_plate_structural_surfaces(wall)[0]
    after = _get_open_points(floor_surface.outline)
    assert all(TOL.is_zero(a.distance_to_point(b)) for a, b in zip(before, after))
    assert TOL.is_close(min(point.z for point in wall_surface.outline.points), floor_surface.frame.point.z)


# =============================================================================
# TimberModel API
# =============================================================================


def _stored_surface_lines(model):
    return [model._graph.edge_attribute(edge, "structural_surface_lines") for edge in model._graph.edges()]


def test_add_structural_surface_lines_reverse_order(l_corner_model):
    model, plate_a, plate_b = l_corner_model
    line = StructuralSurfaceLine(Line(Point(0, 0, 0), Point(1, 0, 0)))

    # the interaction is stored in one order only, both orders must reach it
    model.add_structural_surface_lines(plate_a, plate_b, [line])
    model.add_structural_surface_lines(plate_b, plate_a, [line])

    assert _stored_surface_lines(model) == [[line, line]]


@pytest.mark.parametrize("reverse", [False, True])
def test_remove_structural_surface_lines_either_order(l_corner_model, reverse):
    model, plate_a, plate_b = l_corner_model
    line = StructuralSurfaceLine(Line(Point(0, 0, 0), Point(1, 0, 0)))
    model.add_structural_surface_lines(plate_a, plate_b, [line])

    if reverse:
        model.remove_structural_surface_lines(plate_b, plate_a)
    else:
        model.remove_structural_surface_lines(plate_a, plate_b)

    assert not any(_stored_surface_lines(model))


def test_remove_plate_structural_surfaces(l_corner_model):
    model, plate_a, plate_b = l_corner_model
    _solve(model)

    model.remove_plate_structural_surfaces(plate_a)

    assert model.get_plate_structural_surfaces(plate_a) == []
    assert len(model.get_plate_structural_surfaces(plate_b)) == 1


def test_solving_again_replaces_surfaces_and_lines(l_corner_model):
    model, plate_a, plate_b = l_corner_model
    _solve(model)
    surfaces, lines = _solve(model)

    assert len(model.get_plate_structural_surfaces(plate_a)) == 1
    assert len(model.get_plate_structural_surfaces(plate_b)) == 1
    assert _stored_surface_lines(model) == [lines]
    # the lines point at the surfaces of this run, not at the replaced ones
    assert {line.parent_surface.guid for line in lines} == {surface.guid for surface in surfaces}


def test_add_structural_surface_lines_raises_without_interaction():
    model = TimberModel()
    plate_a = _plate([Point(0, 0, 0), Point(100, 0, 0), Point(100, 100, 0), Point(0, 100, 0)])
    plate_b = _plate([Point(500, 0, 0), Point(600, 0, 0), Point(600, 100, 0), Point(500, 100, 0)])
    model.add_element(plate_a)
    model.add_element(plate_b)

    with pytest.raises(ValueError):
        model.add_structural_surface_lines(plate_a, plate_b, [])


def test_model_json_roundtrip_with_structural_surfaces(l_corner_model):
    model, _, _ = l_corner_model
    _solve(model)

    restored = json_loads(json_dumps(model))

    plates = {str(plate.guid): plate for plate in restored.plates}
    surfaces = {}
    for plate in plates.values():
        plate_surfaces = restored.get_plate_structural_surfaces(plate)
        assert len(plate_surfaces) == 1
        assert plate_surfaces[0].parent_plate is plate
        surfaces[str(plate_surfaces[0].guid)] = plate_surfaces[0]

    lines = [line for edge in restored._graph.edges() for line in restored._graph.edge_attribute(edge, "structural_surface_lines") or []]
    assert len(lines) == 2
    for line in lines:
        assert line.line_type == "connection"
        assert line.parent_plate is plates[line.parent_plate_guid]
        assert line.parent_surface is surfaces[line.parent_surface_guid]


# =============================================================================
# StructuralGraph
# =============================================================================


def test_structural_graph_surface_boundary_has_no_self_loops(l_corner_model):
    model, _, _ = l_corner_model
    _solve(model)

    sg = StructuralGraph.from_model(model)

    assert not [(u, v) for u, v in sg.edges() if u == v]
    # two quads, four boundary edges each
    assert len(list(sg.surface_boundary_edges)) == 8
    for surface in sg.surfaces:
        assert len(surface["boundary_nodes"]) == 4


def test_structural_graph_connection_keeps_boundary(l_corner_model):
    model, _, _ = l_corner_model
    _, lines = _solve(model)

    sg = StructuralGraph.from_model(model)

    connection_edges = list(sg.surface_connection_edges)
    assert len(connection_edges) == 1
    u, v = connection_edges[0]
    # the connection lies on a boundary edge, which must not be overwritten
    assert (u, v) in list(sg.surface_boundary_edges)
    # both plates' connection lines are kept
    assert sg.surface_lines(u, v) == lines


# =============================================================================
# Beam generators and fasteners
# =============================================================================


def test_effective_centerline_default_is_in_mm():
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)

    # 100 mm beyond the end is within the 300 mm default, 500 mm is not
    assert TOL.is_close(effective_centerline(beam, include_points=[Point(1100, 0, 0)]).length, 1100)
    assert TOL.is_close(effective_centerline(beam, include_points=[Point(1500, 0, 0)]).length, 1000)


def test_beam_fastener_interactions_are_skipped(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    fastener = mocker.MagicMock(spec=Fastener)

    joint = mocker.MagicMock(spec=Joint)
    joint.interactions = [(beam, fastener)]
    joint.location = Point(500, 0, 0)

    segments = SimpleBeamSegmentGenerator().generate_segments(beam, [joint])
    connectors = SimpleJointConnectorGenerator().generate_connectors(joint)

    # falls back to the joint location to split the beam
    assert len(segments) == 2
    assert TOL.is_zero(segments[0].line.end.distance_to_point(Point(500, 0, 0)))
    assert connectors == []
