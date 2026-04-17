from compas.geometry import Box
from compas.geometry import Frame
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import GeometryPart


def test_fastener():
    # create a dummy main_part
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener(main_part=GeometryPart(geo))

    assert fastener
    assert isinstance(fastener, Fastener)
    assert len(fastener.parts) == 1
    assert fastener.frame.point == Frame.worldXY().point
    assert fastener.frame.xaxis == Frame.worldXY().xaxis
    assert fastener.frame.yaxis == Frame.worldXY().yaxis


def test_fastener_target_frames():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener(main_part=GeometryPart(geo))

    assert len(fastener.target_frames) == 0

    fastener.target_frames = [Frame([1, 2, 3], [0, 1, 0], [0, 0, 1]), Frame([4, 5, 6], [1, 0, 0], [0, 1, 0])]

    assert len(fastener.target_frames) == 2
    assert all(isinstance(frame, Frame) for frame in fastener.target_frames)
    assert fastener.target_frames[0].point == [1, 2, 3]
    assert fastener.target_frames[1].point == [4, 5, 6]


def test_fastener_instances():
    box = Box(1, 1, 1)
    geo = box.to_mesh()
    fastener = Fastener(main_part=GeometryPart(geo))
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
    fastener = Fastener(main_part=GeometryPart(geo))

    part1 = GeometryPart(geo, frame=Frame([1, 0, 0], [0, 1, 0], [0, 0, 1]))
    part2 = GeometryPart(geo, frame=Frame([0, 1, 0], [1, 0, 0], [0, 0, 1]))

    fastener.add_part(part1)
    fastener.add_child_part(part2, parent=part1)

    assert len(fastener.parts) == 3
    assert fastener.get_parent(part1) == fastener.main_part
    assert fastener.get_parent(part2) == part1
    assert fastener.get_children(part1) == [part2]
