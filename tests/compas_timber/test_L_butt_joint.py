from compas.geometry import Frame
from compas_timber.elements import Beam
from compas_timber.connections import LButtJoint


def test_L_butt_joint_create():
    beam_a = Beam(frame=Frame([0, 0, 0], [1, 0, 0], [0, 1, 0]), width=100, height=200, length=100)
    beam_b = Beam(frame=Frame([0, 0, 0], [0, 1, 0], [1, 0, 0]), width=100, height=200, length=100)

    joint = LButtJoint(beam_a, beam_b, mill_depth=50, small_beam_butts=True, modify_cross=True)

    joint.add_features()
