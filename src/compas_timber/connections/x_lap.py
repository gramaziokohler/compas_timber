from ..connections.joint import Joint


class XLapJoint(Joint):
    def __init__(self, assembly, beamA, beamB):

        super(XLapJoint, self).__init__(assembly, [beamA, beamB])

    @property
    def joint_type(self):
        return "X-Lap"

    def add_feature(self):
        pass
