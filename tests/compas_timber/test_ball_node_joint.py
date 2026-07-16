from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import BallNodeJoint
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import BallNodeCore, BallNodeFastener, BallNodeFastenerParameters, BallNodePlate, BallNodeRod


def test_ball_node_joint():
    centerlines = [Line([1, 1, 1], [100, 100, 100]), Line([1, 1, 1], [100, -50, 30]), Line([1, 1, 1], [-100, -20, -60]), Line([1, 1, 1], [-100, 100, 80])]
    beams = [Beam.from_centerline(centerline, 10, 30) for centerline in centerlines]

    model = TimberModel()
    for beam in beams:
        model.add_element(beam)

    # the joint creates its ball-node fastener; pass parameters to shape it
    joint = BallNodeJoint.create(model, *beams, parameters=BallNodeFastenerParameters(ball_diameter=8, rods_length=10, plate_thickness=2, plate_depth=10))
    assert joint

    model.process_joinery()
    model.process_fasteners()

    model_joints = list(model.joints)
    model_fasteners = list(model.fasteners)
    model_beams = list(model.beams)

    assert len(model_joints) == 1
    assert isinstance(model_joints[0], BallNodeJoint)

    assert len(model_fasteners) == 1
    fastener = model_fasteners[0]
    assert isinstance(fastener, Fastener)

    # the parts form a hierarchy: fastener -> core -> rod -> plate
    assert len(fastener.parts) == 1  # the core is the fastener's only direct child
    core = fastener.parts[0]
    assert isinstance(core, BallNodeCore)
    assert len(core.parts) == 4  # one rod per beam, all children of the core
    assert all(isinstance(rod, BallNodeRod) for rod in core.parts)
    for rod in core.parts:
        assert len(rod.parts) == 1  # each rod owns its plate
        assert isinstance(rod.parts[0], BallNodePlate)
    assert len(fastener.all_parts) == 9  # 1 core + 4 rods + 4 plates

    assert len(model_beams) == 4
    assert all(isinstance(beam, Beam) for beam in model_beams)

    for beam in model_beams:
        assert len(beam.features) == 2
        feature_names = [type(f).__name__ for f in beam.features]
        assert "Slot" in feature_names
        assert "JackRafterCut" in feature_names


def test_ball_node_model_serialization():
    centerlines = [Line([1, 1, 1], [100, 100, 100]), Line([1, 1, 1], [100, -50, 30]), Line([1, 1, 1], [-100, -20, -60]), Line([1, 1, 1], [-100, 100, 80])]
    beams = [Beam.from_centerline(centerline, 10, 30) for centerline in centerlines]

    model = TimberModel()
    for beam in beams:
        model.add_element(beam)

    parameters = BallNodeFastenerParameters(ball_diameter=8, rods_length=10, plate_thickness=2, plate_depth=10)
    BallNodeJoint.create(model, *beams, parameters=parameters)

    reconstructed_model = json_loads(json_dumps(model))

    # the joint survives, carrying its parameters
    rec_joints = list(reconstructed_model.joints)
    assert len(rec_joints) == 1
    assert isinstance(rec_joints[0], BallNodeJoint)
    assert isinstance(rec_joints[0].parameters, BallNodeFastenerParameters)
    assert rec_joints[0].parameters.__data__ == parameters.__data__

    # the fastener survives, carrying its parameters and its nested part hierarchy (fastener -> core -> rod -> plate)
    rec_fasteners = list(reconstructed_model.fasteners)
    assert len(rec_fasteners) == 1
    fastener = rec_fasteners[0]
    assert isinstance(fastener, BallNodeFastener)
    assert fastener.parameters.__data__ == parameters.__data__
    assert len(fastener.parts) == 1
    core = fastener.parts[0]
    assert isinstance(core, BallNodeCore)
    assert len(core.parts) == 4
    assert all(isinstance(rod, BallNodeRod) for rod in core.parts)
    for rod in core.parts:
        assert len(rod.parts) == 1
        assert isinstance(rod.parts[0], BallNodePlate)
    assert len(fastener.all_parts) == 9


def test_parts_deserialization():
    ball_node = BallNodeCore(diameter=8)
    rod = BallNodeRod(length=10, diameter=2.5, beam=None)
    plate = BallNodePlate(x_size=10, y_size=30, thickness=2, frame=rod.frame, plate_depth=10, rod=rod, ball=ball_node)

    assert isinstance(ball_node, BallNodeCore)
    assert isinstance(rod, BallNodeRod)
    assert isinstance(plate, BallNodePlate)

    reconstructed_ball_node = json_loads(json_dumps(ball_node))
    reconstructed_rod = json_loads(json_dumps(rod))
    reconstructed_plate = json_loads(json_dumps(plate))

    assert isinstance(reconstructed_ball_node, BallNodeCore)
    assert isinstance(reconstructed_rod, BallNodeRod)
    assert isinstance(reconstructed_plate, BallNodePlate)
    assert reconstructed_ball_node.diameter == ball_node.diameter
    assert reconstructed_rod.length == rod.length
    assert reconstructed_rod.diameter == rod.diameter
    assert reconstructed_plate.x_size == plate.x_size
    assert reconstructed_plate.y_size == plate.y_size
    assert reconstructed_plate.thickness == plate.thickness
    assert reconstructed_plate.plate_depth == plate.plate_depth
    assert reconstructed_plate.frame.point == plate.frame.point
    assert reconstructed_plate.frame.xaxis == plate.frame.xaxis
    assert reconstructed_plate.frame.yaxis == plate.frame.yaxis
