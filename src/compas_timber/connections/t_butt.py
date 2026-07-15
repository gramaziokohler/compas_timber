from compas.geometry import Frame
from compas.geometry import Plane

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
        cross_beam = self.cross_beam
        main_beam = self.main_beam

        # the fastener is defined in the frame shared by both beams; for now only beams with a common parent are supported
        if main_beam.parent is not cross_beam.parent:
            raise ValueError("Fastener anchors require both beams to share the same parent, got {!r} and {!r}.".format(main_beam.parent, cross_beam.parent))

        # centered on the intersection of the two centerlines
        (cross_point, _), (main_point, _) = intersection_line_line_param(cross_beam.centerline, main_beam.centerline)
        intersection_point = (main_point + cross_point) * 0.5

        # the plate straddles the joint on the two cross beam faces flanking the face the main beam butts into
        butt_index = self.cross_beam_ref_side_index
        anchors = []
        for face_index in [(butt_index + 1) % 4, (butt_index - 1) % 4]:
            face = cross_beam.ref_sides[face_index]
            point = Plane.from_frame(face).closest_point(intersection_point)
            frame = Frame(point, face.xaxis, face.yaxis)

            # TODO: the anchor frames need to be with respect to the parent coordinate system, but this requires properly structuring fasteners as Elements in the model
            # to get the right transformation, we should do that in the end.
            anchors.append(FastenerAnchor(frame, AnchorKind.FACE, [cross_beam, main_beam], ref_side_index=face_index, role="side_face"))

        return FastenerAnchors(anchors)
