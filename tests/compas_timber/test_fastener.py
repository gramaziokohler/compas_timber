from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Transformation

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import GeometryPart
from compas_timber.fasteners import PlateFastener
from compas_timber.model import TimberModel


def test_fastener():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo))

    assert fastener
    assert isinstance(fastener, Fastener)
    assert len(fastener.parts) == 1
    assert fastener.frame.point == Frame.worldXY().point
    assert fastener.frame.xaxis == Frame.worldXY().xaxis
    assert fastener.frame.yaxis == Frame.worldXY().yaxis


def test_fastener_geometry_aggregates_parts():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo, frame=Frame([1, 0, 0], [0, 1, 0], [0, 0, 1])))
    fastener.add_part(GeometryPart(geo, frame=Frame([0, 1, 0], [1, 0, 0], [0, 0, 1])))

    # the fastener has no geometry of its own; it aggregates the geometry of its parts
    assert len(fastener.geometry) == 2


def test_model_fasteners_graph():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo, frame=Frame(Point(0, -5, 20), [1, 0, 0], [0, 0, 1])))
    fastener.add_part(GeometryPart(geo, frame=Frame(Point(0, 5, 20), [-1, 0, 0], [0, 0, 1])))

    model.add_fastener(fastener, [main_beam, cross_beam])
    graph = model.graph

    # the fastener and its parts are now regular elements in the model
    assert len(list(model.fasteners)) == 1
    assert model.fasteners[0] is fastener
    assert len(fastener.parts) == 2
    assert all(part.parent is fastener for part in fastener.parts)

    assert graph.has_edge((cross_beam.graphnode, main_beam.graphnode)) or graph.has_edge((main_beam.graphnode, cross_beam.graphnode))

    if graph.has_edge((cross_beam.graphnode, main_beam.graphnode)):
        edge = (cross_beam.graphnode, main_beam.graphnode)
    else:
        edge = (main_beam.graphnode, cross_beam.graphnode)

    # the edge references the single fastener by guid
    edge_fasteners = graph.edge_attribute(edge, "fasteners")
    assert edge_fasteners == [str(fastener.guid)]


def test_model_deserialization():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(2000, 0, 0)), width=50, height=50)
    main_beam = Beam.from_centerline(Line(Point(1000, 0, 0), Point(1000, 1000, 0)), width=50, height=50)
    model.add_elements([cross_beam, main_beam])

    joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=10)

    fastener = PlateFastener(width=40, height=50, thickness=5, recess=5, recess_offset=1)
    fastener.bind(joint.fastener_anchors.of_kind(AnchorKind.FACE))
    model.add_fastener(fastener, joint.beams)

    reconstructed_model = json_loads(json_dumps(model))

    rec_fasteners = list(reconstructed_model.fasteners)
    assert len(rec_fasteners) == 1
    assert isinstance(rec_fasteners[0], PlateFastener)
    # the parts survive as children of the fastener in the reconstructed model tree
    assert len(rec_fasteners[0].parts) == 2
    from compas_timber.fasteners import RectangularPlate

    assert all(isinstance(part, RectangularPlate) for part in rec_fasteners[0].parts)


def test_fastener_part_placement_via_transformation():
    plate_geo = Box(1, 1, 1).to_mesh()
    part = GeometryPart(plate_geo)
    part.transformation = Transformation.from_frame(Frame(Point(3, 4, 5), [1, 0, 0], [0, 1, 0]))

    assert part.frame.point == Point(3, 4, 5)
