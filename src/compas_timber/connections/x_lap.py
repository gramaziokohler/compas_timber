__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from ..connections.joint import Joint


class XLapJoint(Joint):
    def __init__(self, assembly, beamA, beamB):

        super(XLapJoint, self).__init__(assembly, [beamA, beamB])

    @property
    def joint_type(self):
        return "X-Lap"

    def add_feature(self):
        pass
