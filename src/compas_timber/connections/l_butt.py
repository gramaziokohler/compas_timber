from compas.geometry import close
from compas.geometry import Frame

from compas_timber.connections import Joint
from compas_timber.connections import beam_side_incidence


class LButtJoint(Joint):
    def __init__(self, assembly, main_beam, cross_beam):
        super(LButtJoint, self).__init__(assembly, [main_beam, cross_beam])
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
        data_dict.update(super(LButtJoint, self).data)
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
            isinstance(other, LButtJoint)
            and super(LButtJoint, self).__eq__(other)
            and self.main_beam_key == other.main_beam_key
            and self.cross_beam_key == other.cross_beam_key
            and close(self.gap, other.gap, tol)
        )

    @property
    def joint_type(self):
        return "L-Butt"

    @property
    def main_beam(self):
        return self.assembly.find_by_key(self.main_beam_key)

    @property
    def cross_beam(self):
        return self.assembly.find_by_key(self.cross_beam_key)

    @property
    def cutting_plane_main(self):
        angles_faces = beam_side_incidence(self.main_beam, self.cross_beam)
        cfr = min(angles_faces, key = lambda x: x[0])[1]
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis*-1.0) #flip normal
        return cfr
    
    @property
    def cutting_plane_cross(self):
        angles_faces = beam_side_incidence(self.cross_beam, self.main_beam)
        cfr = max(angles_faces, key = lambda x: x[0])[1]
        return cfr


    def add_features(self):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        In a L-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).
        """
        cfr_main = self.cutting_plane_main
        cfr_cross = self.cutting_plane_cross

        self.main_beam.add_feature(self.main_beam.extension_to_plane(cfr_main), "extend")
        self.main_beam.add_feature(cfr_main, "trim")        
        self.cross_beam.add_feature(self.cross_beam.extension_to_plane(cfr_cross), "extend")
        #self.cross_beam.add_feature(cfr_cross, "trim")




if __name__ == "__main__":

    pass
