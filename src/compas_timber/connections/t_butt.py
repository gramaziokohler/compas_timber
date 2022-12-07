from compas.geometry import close
from compas.geometry import Frame
from compas.geometry import BrepTrimmingError

from compas_timber.connections import Joint
from compas_timber.connections import beam_side_incidence
from compas_timber.connections import BeamJoinningError

class TButtJoint(Joint):
    def __init__(self, assembly=None, main_beam=None, cross_beam=None):
    	#TODO: try if possible remove default Nones
        super(TButtJoint, self).__init__(assembly, [main_beam, cross_beam])
        #TODO: make it protected attribute?
        self.main_beam_key = None
        self.cross_beam_key = None
        
        #TODO: remove direct ref, replace with assembly look up
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.gap = None
        self.features = []

    @property
    def data(self):
        data_dict = {
            "main_beam_key": self.main_beam.key,
            "cross_beam_key": self.cross_beam.key,
            "gap": self.gap,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @data.setter
    def data(self, value):
        Joint.data.fset(self, value)
        self.main_beam_key = value["main_beam_key"]
        self.cross_beam_key = value["cross_beam_key"]
        self.gap = value["gap"]

    def __eq__(self, other):
        return (
            isinstance(other, TButtJoint)
            and super(TButtJoint, self).__eq__(other)
            and self.main_beam_key == other.main_beam_key
            and self.cross_beam_key == other.cross_beam_key
        )

    @property
    def joint_type(self):
        return "T-Butt"

    @Joint.assembly.setter
    def assembly(self, assembly):
        Joint.assembly.fset(self, assembly)
        self.main_beam = assembly.find_by_key(self.main_beam_key)
        self.cross_beam = assembly.find_by_key(self.cross_beam_key)


    #@property
    #def main_beam(self):
    #    return self.assembly.find_by_key(self.main_beam_key)

    #@property
    #def cross_beam(self):
    #    return self.assembly.find_by_key(self.cross_beam_key)

    @property
    def cutting_plane(self):
        angles_faces = beam_side_incidence(self.main_beam, self.cross_beam)
        cfr = min(angles_faces, key = lambda x: x[0])[1]
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis)
        return cfr

    def add_features(self, apply=False):
        """
        Adds the feature definitions (geometry, operation) to the involved beams.
        In a T-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).
        """
        # TODO: joint should only remove the features it has created!
        # TODO: i.e. self.main_beam.clear_features(self.features)
        # TODO: but that doesn't seem to work for some reason.. WIP
        #if self.features: self.main_beam.clear_features()


        #TODO: add extension
        #self.main_beam.add_feature(self.main_beam.extension_to_plane(cfr_main), "extend")
        
        feature = self.main_beam.add_geometry_feature(self.cutting_plane, "trim")
        self.features.append(feature)
        
        if apply:
            try:
                feature.apply()
            except BrepTrimmingError:
                msg = "Failed trimming beam: {} with cutting plane: {}. Does it intersect with beam: {}".format(
                    self.main_beam, self.cutting_plane, self.cross_beam
                )
                raise BeamJoinningError(msg)
    

if __name__ == "__main__":

    pass
