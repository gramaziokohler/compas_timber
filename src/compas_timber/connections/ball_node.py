from __future__ import annotations

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import intersection_line_line

from compas_timber.elements import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import BallNodeFastener
from compas_timber.fasteners import BallNodeFastenerParameters
from compas_timber.fasteners import FastenerAnchor
from compas_timber.fasteners import FastenerAnchors
from compas_timber.utils import intersection_line_line_param

from .joint import Joint
from .solver import JointTopology


class BallNodeJoint(Joint):
    """Represents a ball node type joint which joins the ends of multiple beams.

    Please use `BallNodeJoint.create()` to properly create an instance of this class and associate it with an model.

    The joint only describes *where* the beams meet; it does not build the fastener. It publishes a single ``POINT``
    anchor at the node (see :attr:`fastener_anchors`) that a joint-agnostic fastener (e.g.
    :class:`~compas_timber.fasteners.BallNodeFastener`) binds to. This keeps the joint decoupled from any particular
    fastener implementation.

    Parameters
    ----------
    elements : list(:class:`~compas_timber.elements.Beam`)
        A list of beams to be joined together by this joint.
    parameters : :class:`~compas_timber.fasteners.BallNodeFastenerParameters`, optional
        The parameters that shape the ball-node fastener this joint creates. Defaults to an instance with all default
        values.

    Attributes
    ----------
    elements : list(:class:`~compas_timber.elements.Beam`)
        The beams joined by this joint.
    parameters : :class:`~compas_timber.fasteners.BallNodeFastenerParameters`
        The parameters that shape the ball-node fastener this joint creates.
    location : Point
        The location of the joint, the intersection of the first two beams' centerlines.
    node_point : Point
        The point at which the beams are joined, essentially the average of their intersection points.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_Y
    MAX_ELEMENT_COUNT = None

    @property
    def __data__(self):
        data = super().__data__
        data["parameters"] = self.parameters
        return data

    def __init__(self, *elements: Beam, parameters=None, **kwargs):
        super().__init__(elements=elements, **kwargs)
        self.parameters = parameters if parameters is not None else BallNodeFastenerParameters()

    @classmethod
    def create(cls, model, *elements, parameters=None, **kwargs):
        """Create the joint in ``model`` together with its ball-node fastener.

        A ball node joint only makes sense with a ball-node fastener, so ``create`` always builds and attaches one. The
        joint stays decoupled from the fastener's internals: it hands the fastener its published anchors and lets the
        fastener build itself from the given ``parameters``.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joint belong.
        *elements : :class:`~compas_timber.elements.Beam`
            The beams to be joined together.
        parameters : :class:`~compas_timber.fasteners.BallNodeFastenerParameters`, optional
            The parameters that shape the ball-node fastener. Defaults to an instance with all default values.
        **kwargs : dict
            Additional keyword arguments passed to the joint's constructor.

        Returns
        -------
        :class:`~compas_timber.connections.BallNodeJoint`
            The instance of the created joint.

        """
        joint = cls(*elements, parameters=parameters, **kwargs)
        model.add_joint(joint)

        fastener = BallNodeFastener(parameters=joint.parameters)
        fastener.bind(joint.fastener_anchors.of_kind(fastener.ACCEPTS))
        model.add_fastener(fastener, joint.beams)
        return joint

    @property
    def beams(self):
        """Returns the beams joined by this joint."""
        return self.elements

    @property
    def location(self):
        """Returns the location of the joint, which is the average of the endpoints of the beams."""
        point = Point(*intersection_line_line(self.beams[0].centerline, self.beams[1].centerline)[0])
        return point

    @property
    def node_point(self):
        """Returns the point at which the beams are joined, essentially the average of their intersection points."""
        beams = self.beams
        cpt = Point(0, 0, 0)
        count = 0
        for i, beam in enumerate(beams):
            points = intersection_line_line_param(beams[i - 1].centerline, beam.centerline)  # TODO: include Tolerance check here.
            if points[0][0] is not None and points[1][0] is not None:
                cpt += points[1][0]
                count += 1
        self._node_point = cpt * (1.0 / count)
        return self._node_point

    @property
    def fastener_anchors(self):
        """Publish the place on this joint where a fastener may attach.

        A ball node exposes a single ``POINT`` anchor at the node where the beams meet. The anchor references all the
        joined beams, so a fastener bound here can build its parts (rods, plates, ...) from the beams' geometry.

        Returns
        -------
        :class:`~compas_timber.fasteners.FastenerAnchors`
            The anchors available on this joint.
        """
        frame = Frame(self.node_point, [1, 0, 0], [0, 1, 0])
        anchor = FastenerAnchor(frame=frame, kind=AnchorKind.POINT, elements=list(self.beams), role="node")
        return FastenerAnchors([anchor])

    def add_extensions(self):
        pass

    def add_features(self):
        pass
