from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import TStepJoint
from compas_timber.connections import TBirdsmouthJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import XNotchJoint
from compas_timber.connections import TLapJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import LFrenchRidgeLapJoint
from compas_timber.connections import TDovetailJoint
from compas_timber.connections import BallNodeJoint
from compas_timber.connections import LTenonMortiseJoint
from compas_timber.connections import TTenonMortiseJoint
from compas_timber.connections import YButtJoint
from compas_timber.connections import TOliGinaJoint


def test_get_createable_joints():
    from compas_timber.ghpython import get_createable_joints

    joints = get_createable_joints()

    createable_joints = [
        TButtJoint,
        LButtJoint,
        TStepJoint,
        TBirdsmouthJoint,
        LMiterJoint,
        XLapJoint,
        XNotchJoint,
        TLapJoint,
        LLapJoint,
        LFrenchRidgeLapJoint,
        TDovetailJoint,
        BallNodeJoint,
        LTenonMortiseJoint,
        TTenonMortiseJoint,
        YButtJoint,
        TOliGinaJoint,
    ]

    for joint in createable_joints:
        assert joint in joints
