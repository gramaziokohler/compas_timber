from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line

from compas_model.interactions import Interaction

from .solver import JointTopology


class BeamJoinningError(Exception):
    """Indicates that an error has occurred while trying to join two or more beams.

    This error should indicate that an error has occurred while calculating the features which
    should be applied by this joint.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams that were supposed to be joined.
    debug_geometries : list(:class:`~compas.geometry.Geometry`)
        A list of geometries that can be used to visualize the error.
    debug_info : str
        A string containing debug information about the error.
    joint : :class:`~compas_timber.connections.Joint`
        The joint that was supposed to join the beams.

    """

    def __init__(self, beams, joint, debug_info=None, debug_geometries=None):
        super(BeamJoinningError, self).__init__()
        self.beams = beams
        self.joint = joint
        self.debug_info = debug_info
        self.debug_geometries = debug_geometries or []


class Joint(Interaction):
    """Base class for a joint connecting two beams.

    This is a base class and should not be instantiated directly.
    Use the `create()` class method of the respective implementation of `Joint` instead.

    Attributes
    ----------
    beams : tuple(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    ends : dict(:class:`~compas_timber.parts.Beam`, str)
        A map of which end of each beam is joined by this joint.
    frame : :class:`~compas.geometry.Frame`
        The frame of the joint.
    key : str
        A unique identifier for this joint.
    features : list(:class:`~compas_timber.parts.Feature`)
        A list of features that were added to the beams by this joint.
    attributes : dict
        A dictionary of additional attributes for this joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN

    def __init__(self, **kwargs):
        super(Joint, self).__init__(name=self.__class__.__name__)

    @property
    def beams(self):
        raise NotImplementedError

    def add_features(self):
        """Adds the features defined by this joint to affected beam(s).

        Raises
        ------
        :class:`~compas_timber.connections.BeamJoinningError`
            Should be raised whenever the joint was not able to calculate the features to be applied to the beams.

        """
        raise NotImplementedError

    def restore_beams_from_keys(self):
        """Restores the reference to the beams associate with this joint.

        During serialization, :class:`compas_timber.parts.Beam` objects
        are serialized by :class:`compas_timber.assembly`. To avoid circular references, Joint only stores the keys
        of the respective beams.

        This method is called by :class:`compas_timber.assembly` during de-serialization to restore the references.
        Since the roles of the beams are joint specific (e.g. main/cross beam) this method should be implemented by
        the concrete implementation.

        Examples
        --------
        See :class:`compas_timber.connections.TButtJoint`.

        """
        raise NotImplementedError

    @classmethod
    def create(cls, assembly, *beams, **kwargs):
        """Creates an instance of this joint and creates the new connection in `assembly`.

        `beams` are expected to have been added to `assembly` before calling this method.

        This code does not verify that the given beams are adjacent and/or lie in a topology which allows connecting
        them. This is the responsibility of the calling code.

        A `ValueError` is raised if `beams` contains less than two `Beam` objects.

        Parameters
        ----------
        assemebly : :class:`~compas_timber.assembly.Assembly`
            The assembly to which the beams and this joing belong.
        beams : list(:class:`~compas_timber.parts.Beam`)
            A list containing two beams that whould be joined together

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """

        if len(beams) < 2:
            raise ValueError("Expected at least 2 beams. Got instead: {}".format(len(beams)))
        joint = cls(*beams, **kwargs)
        assembly.add_joint(joint, beams)
        joint.add_features()
        return joint

    @property
    def ends(self):
        """Returns a map of ehich end of each beam is joined by this joint."""

        self._ends = {}
        for index, beam in enumerate(self.beams):
            start_distance = min(
                [
                    beam.centerline.start.distance_to_point(self.beams[index - 1].centerline.start),
                    beam.centerline.start.distance_to_point(self.beams[index - 1].centerline.end),
                ]
            )
            end_distance = min(
                [
                    beam.centerline.end.distance_to_point(self.beams[index - 1].centerline.start),
                    beam.centerline.end.distance_to_point(self.beams[index - 1].centerline.end),
                ]
            )
            if start_distance < end_distance:
                self._ends[str(beam.key)] = "start"
            else:
                self._ends[str(beam.key)] = "end"

        return self._ends

    @staticmethod
    def get_face_most_towards_beam(beam_a, beam_b, ignore_ends=True):
        """Of all the faces of `beam_b`, returns the one whose normal most faces `beam_a`.

        This is done by calculating the inner-product of `beam_a`'s centerline which each of the face normals of `beam_b`.
        The face with the result closest to 1 is chosen.

        Parameters
        ----------
        beam_a : :class:`~compas_timber.parts.Beam`
            The beam that attaches with one of its ends to `beam_b`.
        beam_b : :class:`~compas_timber.parts.Beam`
            The other beam.
        ignore_ends : bool, optional
            If True, the faces at each end of `beam_b` are ignored.

        Returns
        -------
        tuple(face_index, :class:`~compas.geometry.Frame`)
            Tuple containing the index of the chosen face and a frame at the center of if.

        """
        face_dict = Joint._beam_side_incidence(beam_a, beam_b, ignore_ends)
        face_index = max(face_dict, key=face_dict.get)  # type: ignore
        return face_index, beam_b.faces[face_index]

    @staticmethod
    def get_face_most_ortho_to_beam(beam_a, beam_b, ignore_ends=True):
        """Of all the faces of `beam_b`, returns the one whose normal is most orthogonal to `beam_a`.

        This is done by calculating the inner-product of `beam_a`'s centerline which each of the face normals of `beam_b`.
        The face with the result closest to 0 is chosen.

        Parameters
        ----------
        beam_a : :class:`~compas_timber.parts.Beam`
            The beam that attaches with one of its ends to `beam_b`.
        beam_b : :class:`~compas_timber.parts.Beam`
            The other beam.
        ignore_ends : bool, optional
            If True, the faces at each end of `beam_b` are ignored.

        Returns
        -------
        tuple(face_index, :class:`~compas.geometry.Frame`)
            Tuple containing the index of the chosen face and a frame at the center of if.

        """
        face_dict = Joint._beam_side_incidence(beam_a, beam_b, ignore_ends)
        face_index = min(face_dict, key=face_dict.get)  # type: ignore
        return face_index, beam_b.faces[face_index]

    @staticmethod
    def _beam_side_incidence(beam_a, beam_b, ignore_ends=True):
        """Returns a map of face indices of beam_b and the angle of their normal with beam_a's centerline.

        This is used to find a cutting plane when joining the two beams.

        Parameters
        ----------
        beam_a : :class:`~compas_timber.parts.Beam`
            The beam that attaches with one of its ends to the side of beam_b.
        beam_b : :class:`~compas_timber.parts.Beam`
            The other beam.
        ignore_ends : bool, optional
            If True, only the first four faces of `beam_b` are considered. Otherwise all faces are considered.

        Examples
        --------
        >>> face_angles = Joint.beam_side_incidence(beam_a, beam_b)
        >>> closest_face_index = min(face_angles, key=face_angles.get)
        >>> cutting_plane = beam_b.faces[closest_face_index]

        Returns
        -------
        dict(int, float)
            A map of face indices of beam_b and their respective angle with beam_a's centerline.

        """
        # find the orientation of beam_a's centerline so that it's pointing outward of the joint
        # find the closest end
        p1x, _ = intersection_line_line(beam_a.centerline, beam_b.centerline)
        if p1x is None:
            raise AssertionError("No intersection found")

        end, _ = beam_a.endpoint_closest_to_point(Point(*p1x))

        if end == "start":
            centerline_vec = beam_a.centerline.vector
        else:
            centerline_vec = beam_a.centerline.vector * -1

        if ignore_ends:
            beam_b_faces = beam_b.faces[:4]
        else:
            beam_b_faces = beam_b.faces

        face_angles = {}
        for face_index, face in enumerate(beam_b_faces):
            face_angles[face_index] = angle_vectors(face.normal, centerline_vec)

        return face_angles
