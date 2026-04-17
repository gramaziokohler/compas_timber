from compas.geometry import Line

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import BallNodeJoint
from compas_timber.fasteners import Fastener


def test_ball_node_joint():

    centerlines = [Line([1, 1, 1], [100, 100, 100]), Line([1, 1, 1], [100, -50, 30]), Line([1, 1, 1], [-100, -20, -60]), Line([1, 1, 1], [-100, 100, 80])]
    beams = [Beam.from_centerline(centerline, 10, 30) for centerline in centerlines]

    model = TimberModel()
    model.add_elements(beams)

    joint = BallNodeJoint.create(model, beams, ball_diameter=8, rods_length=10)
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
        print(beam.features)
        print(beam)
        assert len(beam.features) == 2
