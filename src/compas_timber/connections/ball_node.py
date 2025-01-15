from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.fabrication import BTLxFeatureDefinition
from compas_timber.elements import BallNodeFastener
from compas_timber.utils import intersection_line_line_param

from .joint import Joint
from .solver import JointTopology


class BallNodeJoint(Joint):
    """Represents a ball node type joint which joins the ends of multiple beams,
    trimming the main beam.

    Please use `BallNodeJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    beams :  list(:class:`~compas_timber.parts.Beam`)
        The beams to be joined.
    base_interface : :class:`~compas_timber.connections.FastenerTimberInterface`
        Describes the interface between the fastener and each of the timber elements.
    ball_diameter : float
        The diameter of the ball node.

    Attributes
    ----------
    elements : list(:class:`~compas_timber.elements.Element`)
        The elements joined by this joint.
    generated_elements : list(:class:`~compas_timber.elements.Element`)
        The elements generated by this joint.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_UNKNOWN
    MAX_ELEMENT_COUNT = None

    @property
    def __data__(self):
        data = super(BallNodeJoint, self).__data__
        data["beam_guids"] = self._beam_guids
        data["ball_diameter"] = self.ball_diameter
        data["fastener_guid"] = self._fastener_guid
        data["base_interface"] = self.fastener.base_interface
        return data

    def __init__(self, beams=None, base_interface=None, ball_diameter=None, **kwargs):
        super(BallNodeJoint, self).__init__(**kwargs)
        self._beam_guids = []
        self.beams = beams or []
        if ball_diameter:
            self.ball_diameter = ball_diameter
        elif beams is not None:
            self.ball_diameter = beams[0].height
        else:
            self.ball_diameter = 100

        self._node_point = None
        self._beam_guids = kwargs.get("beam_guids", None) or [str(beam.guid) for beam in self.beams]
        self._fastener_guid = kwargs.get("fastener_guid", None)
        if not self._fastener_guid:
            self.fastener = BallNodeFastener(self.node_point, self.ball_diameter)
            self.fastener.base_interface = base_interface
            self._fastener_guid = str(self.fastener.guid)

    @property
    def generated_elements(self):
        return [self.fastener]

    @property
    def elements(self):
        return self.beams + [self.generated_elements]

    @property
    def interactions(self):
        for beam in self.beams:
            yield (beam, self.fastener)

    @classmethod
    def create(cls, model, *elements, **kwargs):
        """Creates an instance of the BallNodeJoint and creates the new connection in `model`.

        This differs fom the generic `Joint.create()` method in that it passes the `beams` to
        the constructor of the BallNodeJoint as a list instead of as separate arguments.

        `beams` are expected to have been added to `model` before calling this method.

        This code does not verify that the given beams are adjacent and/or lie in a topology which allows connecting
        them. This is the responsibility of the calling code.

        A `ValueError` is raised if `beams` contains less than two `Beam` objects.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joing belong.
        beams : list(:class:`~compas_timber.parts.Beam`)
            A list containing beams that whould be joined together

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """
        elements = list(elements)
        joint = cls(elements, **kwargs)
        model.add_joint(joint)
        return joint

    @property
    def node_point(self):
        """Returns the point at which the beams are joined, essentially the average of their intersection points."""
        if not self._node_point:
            beams = list(self.beams)
            cpt = Point(0, 0, 0)
            count = 0
            for i, beam in enumerate(beams):
                points = intersection_line_line_param(beams[i - 1].centerline, beam.centerline)  # TODO: include Tolerance check here.
                if points[0][0] is not None and points[1][0] is not None:
                    cpt += points[1][0]
                    count += 1
            self._node_point = cpt * (1.0 / count)
        return self._node_point

    def add_features(self):
        """Adds the features of the joint as generated by `FastenerTimberInterface` to the timber elements.
        In this joint, the fastener adapt to the beams, therefore, the joint creates the FastenerTimberInterface
        and adds it to the fastener.

        """
        assert self.fastener
        for beam in self.beams:
            interface = self.fastener.base_interface.copy()
            pt = beam.centerline.closest_point(self._node_point)
            interface.frame = Frame(pt, Vector.from_start_end(pt, beam.midpoint), beam.frame.zaxis)
            self.fastener.interfaces.append(interface)
            beam.add_features(interface.get_features(beam))

    def restore_beams_from_keys(self, model):
        self.beams = [model.element_by_guid(guid) for guid in self._beam_guids]
        self.fastener = model.element_by_guid(self._fastener_guid)
