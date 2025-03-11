from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Vector
from compas.geometry import Transformation
from compas_timber.elements import Beam
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import BTLxFromGeometryDefinition
from compas_timber.fabrication.double_cut import DoubleCut
from compas_timber.fabrication.jack_cut import JackRafterCut


def test_deferred_drilling():
    width = 60
    height = 120
    centerline = Line(Point(x=0.0, y=0.0, z=0.0), Point(x=1000.0, y=0.0, z=0.0))

    beam = Beam.from_centerline(centerline, width, height)

    test_frame = Frame(Point(500, 0, 0), [-1, 0, 0], [0, 0, -1])
    drill_line = Line(Point(x=0.0, y=0.0, z=-100.0), Point(x=200.0, y=0.0, z=100.0))
    xform = Transformation.from_frame_to_frame(Frame.worldXY(), test_frame)
    t_line = drill_line.transformed(xform)

    diameter = 10.0

    drilling = Drilling.from_line_and_element(drill_line, beam, diameter)
    drilling_def = BTLxFromGeometryDefinition(Drilling, drill_line, beam, diameter=diameter)

    t_drilling = Drilling.from_line_and_element(t_line, beam, diameter)
    t_def = drilling_def.transformed(xform)

    assert drilling_def.feature_from_element(beam).params.as_dict() == drilling.params.as_dict()
    assert t_def.feature_from_element(beam).params.as_dict() == t_drilling.params.as_dict()


def test_deferred_jack_cut():
    width = 60
    height = 120
    centerline = Line(Point(x=0.0, y=0.0, z=0.0), Point(x=1000.0, y=0.0, z=0.0))
    beam = Beam.from_centerline(centerline, width, height)

    test_frame = Frame(Point(500, 0, 0), [-1, 0, 0], [0, 0, -1])
    test_plane = Plane(Point(500, 0, 0), Vector(-1, 0, 1))
    xform = Transformation.from_frame_to_frame(Frame.worldXY(), test_frame)
    t_plane = test_plane.transformed(xform)

    jack_cut = JackRafterCut.from_plane_and_beam(test_plane, beam)
    jack_cut_def = BTLxFromGeometryDefinition(JackRafterCut, test_plane, beam)

    t_jack_cut = JackRafterCut.from_plane_and_beam(t_plane, beam)
    t_def = jack_cut_def.transformed(xform)

    assert jack_cut_def.feature_from_element(beam).params.as_dict() == jack_cut.params.as_dict()
    assert t_def.feature_from_element(beam).params.as_dict() == t_jack_cut.params.as_dict()


def test_deferred_double_cut():
    width = 60
    height = 120
    centerline = Line(Point(x=0.0, y=0.0, z=0.0), Point(x=1000.0, y=0.0, z=0.0))
    beam = Beam.from_centerline(centerline, width, height)

    test_frame = Frame(Point(500, 0, 0), [-1, 0, 0], [0, 0, -1])
    test_planes = [Plane(Point(500, 0, 0), Vector(-1, 0, 1)), Plane(Point(500, 0, 0), Vector(-1, 0, -1))]
    xform = Transformation.from_frame_to_frame(Frame.worldXY(), test_frame)
    t_planes = [plane.transformed(xform) for plane in test_planes]

    double_cut = DoubleCut.from_planes_and_beam(test_planes, beam, ref_side_index=1)
    double_cut_def = BTLxFromGeometryDefinition(DoubleCut, test_planes, beam, ref_side_index=1)

    t_double_cut = DoubleCut.from_planes_and_beam(t_planes, beam, ref_side_index=0)
    double_cut_def_a = BTLxFromGeometryDefinition(DoubleCut, test_planes, beam, ref_side_index=0)
    t_def = double_cut_def_a.transformed(xform)

    assert double_cut_def.feature_from_element(beam).params.as_dict() == double_cut.params.as_dict()
    assert t_def.feature_from_element(beam).params.as_dict() == t_double_cut.params.as_dict()
