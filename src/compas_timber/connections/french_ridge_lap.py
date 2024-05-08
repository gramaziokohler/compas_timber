import math

from compas.geometry import Frame
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors

from .joint import BeamJoinningError
from .joint import Joint
from .solver import JointTopology


class FrenchRidgeLapJoint(Joint):
    """Represents a French Ridge Lap type joint which joins two beam at their ends.

    This joint type is compatible with beams in L topology.

    Please use `LButtJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.TimberAssembly`
        The assembly associated with the beams to be joined.
    beam_a : :class:`~compas_timber.parts.Beam`
        The top beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        The bottom beam to be joined.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    joint_type : str
        A string representation of this joint's type.
    reference_face_indices : dict
        A dictionary containing the indices of the reference faces for both beams.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    def __init__(self, beam_a=None, beam_b=None, drill_diameter=0.0, **kwargs):
        super(FrenchRidgeLapJoint, self).__init__(beams=(beam_a, beam_b), **kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.drill_diameter = float(drill_diameter)
        self.beam_a_key = beam_a.key if beam_a else None
        self.beam_b_key = beam_b.key if beam_b else None
        self.reference_face_indices = {}
        self.check_geometry()

    @property
    def __data__(self):
        data_dict = {
            "beam_a_key": self.beam_a_key,
            "beam_b_key": self.beam_b_key,
        }
        data_dict.update(super(FrenchRidgeLapJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(frame=Frame.__from_data__(value["frame"]), key=value["key"])
        instance.beam_a_key = value["beam_a_key"]
        instance.beam_b_key = value["beam_b_key"]
        return instance

    @property
    def cutting_plane_top(self):
        _, cfr = self.get_face_most_towards_beam(self.beam_a, self.beam_b, ignore_ends=True)
        cfr = Frame(cfr.point, cfr.xaxis, cfr.yaxis * -1.0)  # flip normal
        return cfr

    @property
    def cutting_plane_bottom(self):
        _, cfr = self.get_face_most_towards_beam(self.beam_b, self.beam_a, ignore_ends=True)
        return cfr

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, restores references to the top and bottom beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)
        self._beams = (self.beam_a, self.beam_b)

    def add_extensions(self):
        self.beam_a.add_blank_extension(*self.beam_a.extension_to_plane(self.cutting_plane_top), joint_key=self.key)
        self.beam_b.add_blank_extension(*self.beam_b.extension_to_plane(self.cutting_plane_bottom), joint_key=self.key)

    def add_features(self):
        self.features = []

    def check_geometry(self):
        """
        This method checks whether the parts are aligned as necessary to create French Ridge Lap and determines which face is used as reference face for machining.
        """
        if not (self.beam_a and self.beam_b):
            raise (BeamJoinningError(beams=self.beams, joint=self, debug_info="beams not set"))

        if not (self.beam_a.width == self.beam_b.width and self.beam_a.height == self.beam_b.height):
            raise (BeamJoinningError(beams=self.beams, joint=self, debug_info="beams are not of same size"))

        normal = cross_vectors(self.beam_a.frame.xaxis, self.beam_b.frame.xaxis)

        indices = []

        if angle_vectors(normal, self.beam_a.frame.yaxis) < 0.001:
            indices.append(3)
        elif angle_vectors(normal, self.beam_a.frame.zaxis) < 0.001:
            indices.append(4)
        elif angle_vectors(normal, -self.beam_a.frame.yaxis) < 0.001:
            indices.append(1)
        elif angle_vectors(normal, -self.beam_a.frame.zaxis) < 0.001:
            indices.append(2)
        else:
            raise (
                BeamJoinningError(
                    beams=self.beams,
                    joint=self,
                    debug_info="part not aligned with corner normal, no French Ridge Lap possible",
                )
            )

        if abs(angle_vectors(normal, self.beam_b.frame.yaxis) - math.pi) < 0.001:
            indices.append(3)
        elif abs(angle_vectors(normal, self.beam_b.frame.zaxis) - math.pi) < 0.001:
            indices.append(4)
        elif abs(angle_vectors(normal, -self.beam_b.frame.yaxis) - math.pi) < 0.001:
            indices.append(1)
        elif abs(angle_vectors(normal, -self.beam_b.frame.zaxis) - math.pi) < 0.001:
            indices.append(2)
        else:
            raise (
                BeamJoinningError(
                    beams=self.beams,
                    joint=self,
                    debug_info="part not aligned with corner normal, no French Ridge Lap possible",
                )
            )
        self.reference_face_indices = {str(self.beam_a.key): indices[0], str(self.beam_b.key): indices[1]}
