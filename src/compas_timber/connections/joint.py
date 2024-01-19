from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line

from .solver import JointTopology


def beam_side_incidence(beam1, beam2):
    """Returns a map of faces of beam2 and the angle of their normal with beam1's centerline.

    This is used to find a cutting plane when joining the two beams.

    Parameters
    ----------
    beam1 : :class:`~compas_timber.parts.Beam`
        The beam that attaches with one of its ends to the side of Beam2.
    beam2 : :class:`~compas_timber.parts.Beam`
        The other beam.

    Returns
    -------
    list(tuple(float, :class:`~compas.geometry.Frame`))

    """

    # find the orientation of beam1's centerline so that it's pointing outward of the joint
    #   find the closest end
    p1x, p2x = intersection_line_line(beam1.centerline, beam2.centerline)
    which, _ = beam1.endpoint_closest_to_point(Point(*p1x))

    if which == "start":
        centerline_vec = beam1.centerline.vector
    else:
        centerline_vec = beam1.centerline.vector * -1

    # map faces to their angle with centerline, choose smallest
    angle_face = [(angle_vectors(side.normal, centerline_vec), side) for side in beam2.faces[:4]]
    return angle_face


class BeamJoinningError(BaseException):
    """Indicates that an error has occurred while trying to join two or more beams."""

    pass


class Joint(Data):
    """Base class for a joint connecting two beams.

    This is a base class and should not be instantiated directly.
    Use the `create()` class method of the respective implementation of `Joint` instead.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.

    ends : dict(:class:`~compas_timber.parts.Beam`, str)
        A map of which end of each beam is joined by this joint.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN

    def __init__(self, frame=None, key=None):
        super(Joint, self).__init__()
        self.frame = frame or Frame.worldXY()
        self.key = key

    @property
    def data(self):
        return {"frame": self.frame.data, "key": self.key, "beams": [beam.key for beam in self.beams]}

    @property
    def beams(self):
        raise NotImplementedError

    def add_features(self):
        """Adds the features defined by this joint to affected beam(s)."""
        raise NotImplementedError

    def restore_beams_from_keys(self):
        """Restores the reference to the beams associate with this joint.

        During serialization, :class:`compas_timber.parts.Beam` objects
        are serialized by :class:`compas_timber.assembly`. To avoid circular references, Joint only stores the keys
        of the respective beams.

        This method is called by :class:`compas_timber.assembly during de-serialization to restore the references.
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



