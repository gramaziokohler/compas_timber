from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.fasteners import Fastener
from compas_timber.fasteners import GeometryPart
from compas_timber.model import TimberModel
from compas_timber.elements import Beam


def test_fastener():
    # create a dummy main_part
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


def test_fastener_target_frames():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo))

    assert len(fastener.target_frames) == 0

    fastener.target_frames = [Frame([1, 2, 3], [0, 1, 0], [0, 0, 1]), Frame([4, 5, 6], [1, 0, 0], [0, 1, 0])]

    assert len(fastener.target_frames) == 2
    assert all(isinstance(frame, Frame) for frame in fastener.target_frames)
    assert fastener.target_frames[0].point == [1, 2, 3]
    assert fastener.target_frames[1].point == [4, 5, 6]


def test_fastener_instances():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo))
    fastener.target_frames = [Frame([1, 2, 3], [0, 1, 0], [0, 0, 1]), Frame([4, 5, 6], [1, 0, 0], [0, 1, 0])]

    fastener_instances = fastener.get_fastener_instances()

    assert fastener_instances
    assert len(fastener_instances) == 2
    assert all(isinstance(instance, Fastener) for instance in fastener_instances)
    assert fastener_instances[0].frame.point == [1, 2, 3]
    assert fastener_instances[1].frame.point == [4, 5, 6]

    assert fastener_instances[0].parts[0].frame.point == [1, 2, 3]
    assert fastener_instances[1].parts[0].frame.point == [4, 5, 6]


def test_fastener_parts():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo))

    part1 = GeometryPart(geo, frame=Frame([1, 0, 0], [0, 1, 0], [0, 0, 1]))
    part2 = GeometryPart(geo, frame=Frame([0, 1, 0], [1, 0, 0], [0, 0, 1]))

    fastener.add_part(part1)
    fastener.add_child_part(part2, parent=part1)

    assert len(fastener.parts) == 3
    assert fastener.get_parent(part2) == part1
    assert fastener.get_children(part1) == [part2]


def test_fastener_deserialization():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    part1 = GeometryPart(geo)
    fastener.add_part(part1)
    fastener.target_frames = [Frame([1, 2, 3], [0, 1, 0], [0, 0, 1]), Frame([4, 5, 6], [1, 0, 0], [0, 1, 0])]
    box2 = Box(2, 2, 2)
    geo2 = box2.to_mesh()
    part2 = GeometryPart(geo2, frame=Frame([0, 1, 0], [1, 0, 0], [0, 0, 1]))
    fastener.add_child_part(part2, parent=part1)

    data = fastener.__data__

    reconstructed_fastener = Fastener.from_data(data)
    print(reconstructed_fastener.parts)

    assert reconstructed_fastener
    assert isinstance(reconstructed_fastener, Fastener)
    assert len(reconstructed_fastener.parts) == 2


def test_model_fasteners_graph():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo))
    target_frame1 = Frame(Point(0, -5, 20), [1, 0, 0], [0, 0, 1])
    target_frame2 = Frame(Point(0, 5, 20), [-1, 0, 0], [0, 0, 1])
    fastener.target_frames = [target_frame1, target_frame2]

    model.add_fastener(fastener, [main_beam, cross_beam])
    graph = model.graph

    assert graph.has_edge((cross_beam.graphnode, main_beam.graphnode)) or graph.has_edge((main_beam.graphnode, cross_beam.graphnode))

    if graph.has_edge((cross_beam.graphnode, main_beam.graphnode)):
        edge = (cross_beam.graphnode, main_beam.graphnode)
    else:
        edge = (main_beam.graphnode, cross_beam.graphnode)

    assert graph.edge_attribute(edge, "fasteners") is not None
    assert len(graph.edge_attribute(edge, "fasteners")) == 2


def test_model_deserialization():
    model = TimberModel()
    cross_beam = Beam.from_centerline(Line(Point(-100, 0, 20), Point(100, 0, 20)), width=10, height=20)
    main_beam = Beam.from_centerline(Line(Point(0, 0, 20), Point(0, 0, 200)), width=10, height=20)
    model.add_elements([cross_beam, main_beam])

    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener()
    fastener.add_part(GeometryPart(geo))
    target_frame1 = Frame(Point(0, -5, 20), [1, 0, 0], [0, 0, 1])
    target_frame2 = Frame(Point(0, 5, 20), [-1, 0, 0], [0, 0, 1])
    fastener.target_frames = [target_frame1, target_frame2]

    from compas_timber.connections import TButtJoint

    TButtJoint.create(model, main_beam, cross_beam)

    model.add_fastener(fastener, [main_beam, cross_beam])

    data = model.__data__

    reconstructed_model = TimberModel.__from_data__(data)

    assert reconstructed_model
    assert len(reconstructed_model.fasteners) == 2

    rec_fasteners = list(reconstructed_model.fasteners)

    for i in range(len(rec_fasteners)):
        assert isinstance(rec_fasteners[i], Fastener)
        assert len(rec_fasteners[i].parts) == 1
        assert len(rec_fasteners[i].target_frames) == 0  # it has to be 0 because is a fastener in the model!
        assert isinstance(rec_fasteners[i].parts[0], GeometryPart)
