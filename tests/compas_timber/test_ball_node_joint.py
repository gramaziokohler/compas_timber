from compas.geometry import Line

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import BallNodeJoint
from compas_timber.fasteners import Fastener
from compas_timber.fasteners import BallNode, BallNodePlate, BallNodeRod


def test_ball_node_joint():
    centerlines = [Line([1, 1, 1], [100, 100, 100]), Line([1, 1, 1], [100, -50, 30]), Line([1, 1, 1], [-100, -20, -60]), Line([1, 1, 1], [-100, 100, 80])]
    beams = [Beam.from_centerline(centerline, 10, 30) for centerline in centerlines]

    model = TimberModel()
    for beam in beams:
        model.add_element(beam)

    joint = BallNodeJoint.create(model, *beams, ball_diameter=8, rods_length=10, plate_thickness=2, plate_depth=10)
    assert joint

    model.process_joinery()
    model.process_fasteners()

    model_joints = list(model.joints)
    model_fasteners = list(model.fasteners)
    model_beams = list(model.beams)

    assert len(model_joints) == 1
    assert isinstance(model_joints[0], BallNodeJoint)

    assert len(model_fasteners) == 1
    assert isinstance(model_fasteners[0], Fastener)
    assert len(model_fasteners[0].parts) == 9

    assert len(model_beams) == 4
    assert all(isinstance(beam, Beam) for beam in model_beams)

    for beam in model_beams:
        assert len(beam.features) == 2
        feature_names = [type(f).__name__ for f in beam.features]
        assert "Slot" in feature_names
        assert "JackRafterCut" in feature_names


def test_parts_deserialization():
    ball_node = BallNode(diameter=8)
    rod = BallNodeRod(length=10, diameter=2.5, beam=None)
    plate = BallNodePlate(x_size=10, y_size=30, thickness=2, frame=rod.frame, plate_depth=10, rod=rod, ball=ball_node)

    assert isinstance(ball_node, BallNode)
    assert isinstance(rod, BallNodeRod)
    assert isinstance(plate, BallNodePlate)

    ball_node_data = ball_node.__data__
    rod_data = rod.__data__
    plate_data = plate.__data__

    reconstructed_ball_node = BallNode.from_data(ball_node_data)
    reconstructed_rod = BallNodeRod.from_data(rod_data)
    reconstructed_plate = BallNodePlate.from_data(plate_data)

    assert isinstance(reconstructed_ball_node, BallNode)
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
