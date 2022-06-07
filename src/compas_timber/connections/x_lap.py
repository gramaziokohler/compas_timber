from ..connections.joint import Joint


class XLapJoint(Joint):
    def __init__(self, beamA, beamB, assembly):

        super(XLapJoint, self).__init__([beamA, beamB], assembly)

    @property
    def joint_type(self):
        return 'X-Lap'

    def add_feature(self):
        pass