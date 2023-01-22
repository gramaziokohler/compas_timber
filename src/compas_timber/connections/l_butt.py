from compas.geometry import Frame

from compas_timber.parts import BeamExtensionFeature
from compas_timber.parts import BeamTrimmingFeature

from .joint import Joint
from .joint import beam_side_incidence
from .solver import JointTopology


class LButtJoint(Joint):

    SUPPORTED_TOPOLOGY = JointTopology.L

    def __init__(self, assembly=None, main_beam=None, cross_beam=None):
        super(LButtJoint, self).__init__(assembly, [main_beam, cross_beam])
        self.main_beam_key = main_beam.key
        self.cross_beam_key = cross_beam.key
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.gap = 0.0  # float, additional gap, e.g. for glue
        self.features = []

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

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self, assemly):
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    @property
    def joint_type(self):
        return "L-Butt"

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
        In a T-Butt joint, adds the trimming plane to the main beam (no features for the cross beam).

        """
        if self.features:
            self.main_beam.clear_features(self.features)
            self.cross_beam.clear_features(self.features)
            self.features = []

        main_extend = BeamExtensionFeature(*self.main_beam.extension_to_plane(self.cutting_plane_main))
        main_trim = BeamTrimmingFeature(self.cutting_plane_main)
        cross_extend = BeamExtensionFeature(*self.cross_beam.extension_to_plane(self.cutting_plane_cross))

        self.main_beam.add_feature(main_extend)
        self.main_beam.add_feature(main_trim)
        self.cross_beam.add_feature(cross_extend)
        self.features.extend([main_extend, main_trim, cross_extend])
