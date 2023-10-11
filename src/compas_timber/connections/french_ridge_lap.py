from compas.geometry import Frame
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors


from compas_timber.parts import BeamExtensionFeature
from compas_timber.parts import BeamTrimmingFeature

from .joint import Joint
from .joint import beam_side_incidence
from .solver import JointTopology


class FrenchRidgeLapJoint(Joint):
    """Represents a French Ridge Lap type joint which joins two beam at their ends.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.TimberAssembly`
        The assembly associated with the beams to be joined.
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    joint_type : str
        A string representation of this joint's type.


    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, main_beam=None, cross_beam=None, gap=0.0, frame=None, key=None):
        super(FrenchRidgeLapJoint, self).__init__(frame=frame, key=key)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.features = []
        self.reference_face_indices = None

    @property
    def data(self):
        data_dict = {
            "main_beam_key": self.main_beam_key,
            "cross_beam_key": self.cross_beam_key,
            "gap": self.gap,
        }
        data_dict.update(super(FrenchRidgeLapJoint, self).data)
        return data_dict

    @classmethod
    def from_data(cls, value):
        instance = cls(frame=Frame.from_data(value["frame"]), key=value["key"], gap=value["gap"])
        instance.main_beam_key = value["main_beam_key"]
        instance.cross_beam_key = value["cross_beam_key"]
        return instance

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    @property
    def joint_type(self):
        return "French Ridge Lap"

    @property
    def cutting_plane_main(self):
        angles_faces = beam_side_incidence(self.main_beam, self.cross_beam)
        cfr = max(angles_faces, key=lambda x: x[0])[1]
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        return cfr

    @property
    def cutting_plane_cross(self):
        angles_faces = beam_side_incidence(self.cross_beam, self.main_beam)
        cfr = max(angles_faces, key=lambda x: x[0])[1]
        return cfr

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    def check_geometry(self):
        """
        This method checks whether the parts are aligned as necessary to create French Ridge Lap.
        """
        if not (self.main_beam and self.cross_beam):
            raise ("French Ridge Lap requires 2 beams")

        if not (self.main_beam.width == self.cross_beam.width and self.main_beam.height == self.cross_beam.height):
            raise ("widths and heights for both beams must match for the French Ridge Lap")

        normal = cross_vectors(self.main_beam.frame.xaxis, self.cross_beam.frame.xaxis)

        indices = []

        if angle_vectors(normal, self.main_beam.frame.yaxis) < 0.001:
            indices[0] = 3
        elif angle_vectors(normal, self.main_beam.frame.zaxis) < 0.001:
            indices[0] = 4
        elif angle_vectors(normal, -self.main_beam.frame.yaxis) < 0.001:
            indices[0] = 1
        elif angle_vectors(normal, -self.main_beam.frame.zaxis) < 0.001:
            indices[0] = 2
        else:
            raise ("part not aligned with corner normal, no French Ridge Lap possible")

        if angle_vectors(normal, self.cross_beam.frame.yaxis) < 0.001:
            indices[0] = 3
        elif angle_vectors(normal, self.cross_beam.frame.zaxis) < 0.001:
            indices[0] = 4
        elif angle_vectors(normal, -self.cross_beam.frame.yaxis) < 0.001:
            indices[0] = 1
        elif angle_vectors(normal, -self.cross_beam.frame.zaxis) < 0.001:
            indices[0] = 2
        else:
            raise ("part not aligned with corner normal, no French Ridge Lap possible")

        self.reference_face_indices = (indices[0], indices[1])


    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        if self.features:
            self.main_beam.clear_features(self.features)
            self.cross_beam.clear_features(self.features)
            self.features = []

        main_extend = BeamExtensionFeature(*self.main_beam.extension_to_plane(self.cutting_plane_main))
        cross_extend = BeamExtensionFeature(*self.cross_beam.extension_to_plane(self.cutting_plane_cross))

        self.main_beam.add_feature(main_extend)
        self.cross_beam.add_feature(cross_extend)
        self.features.extend([main_extend, cross_extend])
