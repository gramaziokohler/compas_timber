from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Vector

from compas_timber.elements.beam import Beam
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import FastenerAnchor
from compas_timber.fasteners import FastenerAnchors
from compas_timber.utils import intersection_line_line_param

from .butt_joint import ButtJoint
from .solver import JointTopology


class TButtJoint(ButtJoint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    butt_plane_spec : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=None,
        butt_plane_spec=None,
        force_pocket=False,
        conical_tool=False,
        **kwargs,
    ):
        super(TButtJoint, self).__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            mill_depth=mill_depth,
            butt_plane_spec=butt_plane_spec,
            force_pocket=force_pocket,
            conical_tool=conical_tool,
            **kwargs,
        )

    @property
    def elements(self):
        return self.beams

    @property
    def fastener_anchors(self):
        """Publish the places on this joint where a fastener may attach.

        For a T-Butt, a fastener can sit on either exposed face of the cross beam adjacent to the main beam. Both faces
        are published as ``FACE`` anchors, centered on the intersection of the two centerlines and expressed in the
        coordinate system shared by the two beams.

        Returns
        -------
        :class:`~compas_timber.fasteners.FastenerAnchors`
            The anchors available on this joint.

        Raises
        ------
        ValueError
            If the two beams do not share the same parent, i.e. no common coordinate system is defined.
        """
        assert self.cross_beam is not None, "cross_beam must be defined to compute fastener anchors"
        assert self.main_beam is not None, "main_beam must be defined to compute fastener anchors"
        cross_beam: Beam = self.cross_beam
        main_beam: Beam = self.main_beam

        # the fastener is defined in the frame shared by both beams; for now only beams with a common parent are supported
        if main_beam.parent is not cross_beam.parent:
            raise ValueError("Fastener anchors require both beams to share the same parent, got {!r} and {!r}.".format(main_beam.parent, cross_beam.parent))

        # centered on the intersection of the two centerlines
        (cross_point, _), (main_point, _) = intersection_line_line_param(cross_beam.centerline, main_beam.centerline)
        assert cross_point and main_point
        intersection_point = (main_point + cross_point) * 0.5

        # building the two side anchor, one on the front_side, one on the back_side accordig to Timber Frame
        # the plate straddles the joint on the two cross beam faces flanking the face the main beam butts into
        ref_side_index = self.cross_beam_ref_side_index
        fron_side_frame = cross_beam.front_side(ref_side_index)
        back_side_frame = cross_beam.back_side(ref_side_index)
        opp_side_frame = cross_beam.opp_side(ref_side_index)

        # front anchor
        point = Plane.from_frame(fron_side_frame).closest_point(intersection_point)
        frame = Frame(point, fron_side_frame.xaxis, fron_side_frame.yaxis)
        anchor_front = FastenerAnchor(frame, AnchorKind.FACE, [main_beam, cross_beam], ref_side_index=(ref_side_index + 1) % 4, role="front_face")

        # back anchor
        point = Plane.from_frame(back_side_frame).closest_point(intersection_point)
        frame = Frame(point, back_side_frame.xaxis, back_side_frame.yaxis)
        anchor_back = FastenerAnchor(frame, AnchorKind.FACE, [main_beam, cross_beam], ref_side_index=(ref_side_index - 1) % 4, role="back_face")

        # opp anchor
        point = Plane.from_frame(opp_side_frame).intersection_with_line(self.main_beam.centerline)
        frame = Frame(point, opp_side_frame.xaxis, opp_side_frame.yaxis)
        frame = Frame.from_plane(Plane(point, Vector.from_start_end(main_beam.centerline.midpoint, point)))
        anchor_opp = FastenerAnchor(frame, AnchorKind.AXIS, [main_beam, cross_beam], ref_side_index=(ref_side_index + 2) % 4, role="opposite_face")

        anchors = [anchor_front, anchor_back, anchor_opp]
        return FastenerAnchors(anchors)
