__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas.geometry import close
from compas.geometry import Frame

from compas_timber.connections.joint import Joint
from compas_timber.connections import beam_side_incidence

class TButtJoint(Joint):
    def __init__(self, assembly, main_beam, cross_beam):
        super(TButtJoint, self).__init__(assembly, [main_beam, cross_beam])
        self.main_beam_key = main_beam.key
        self.cross_beam_key = cross_beam.key
        self.gap = 0.0  # float, additional gap, e.g. for glue

    @property
    def data(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "gap": self.gap,
        }
        data_dict.update(super(TButtJoint, self).data)
        return data_dict

    @data.setter
    def data(self, value):
        Joint.data.fset(self, value)
        self.main_beam_key = value["main_beam_key"]
        self.cross_beam_key = value["cross_beam_key"]
        self.gap = value["gap"]

    def __eq__(self, other):
        tol = self.assembly.tol
        return (
            isinstance(other, TButtJoint)
            and super(TButtJoint, self).__eq__(other)
            and self.main_beam_key == other.main_beam_key
            and self.cross_beam_key == other.cross_beam_key
            and close(self.gap, other.gap, tol)
        )

    @property
    def joint_type(self):
        return "T-Butt"

    @property
    def main_beam(self):
        return self.assembly.find_by_key(self.main_beam_key)

    @property
    def cross_beam(self):
        return self.assembly.find_by_key(self.cross_beam_key)

    @property
    def cutting_plane(self):
        angles_faces = beam_side_incidence(self.main_beam, self.cross_beam)
        cfr = min(angles_faces, key = lambda x: x[0])[1]
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis*-1.0) #flip normal
        return cfr

    def add_features(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        """
        cfr_main = self.cutting_plane

        self.main_beam.add_feature(self.main_beam.extension_to_plane(cfr_main), "extend")
        self.main_beam.add_feature(cfr_main, "trim")        

if __name__ == "__main__":

    pass
