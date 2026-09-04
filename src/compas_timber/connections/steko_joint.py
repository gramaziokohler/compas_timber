from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import intersection_line_line
from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fasteners import AnchorKind
from compas_timber.fasteners import FastenerAnchor
from compas_timber.fasteners import FastenerAnchors
from compas_timber.fasteners import StekoFastenerSystem
from compas_timber.fasteners import StekoJointType

from .joint import Joint
from .utilities import beam_ref_side_incidence


class StekoJoint(Joint):
    """
    Steko Joint connecting beam to column
    """

    def __init__(self, steko_column: Beam = None, *steko_beams: Beam, **kwargs):
        super().__init__(
            elements=(steko_beams + (steko_column,)),
            **kwargs,
        )
        self.slot_width = 0.027  # 27mm
        self.slot_depth = 0.07 + 0.07 + 0.07 + 0.045  # according to drawing
        self.slot_padding = 0.04  # 40 mmm

    @classmethod
    def create(cls, model, steko_column, *steko_beams, **kwargs):
        """Create the joint in ``model`` together with its Steko fastener.

        Mirrors :meth:`~compas_timber.connections.BallNodeJoint.create`: the joint stays decoupled from the
        fastener's internals, publishing its anchors and its :attr:`joint_type` and letting the fastener decide how
        to lay itself out.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the beams and this joint belong.
        steko_column : :class:`~compas_timber.elements.Beam`
            The column the beams connect to.
        *steko_beams : :class:`~compas_timber.elements.Beam`
            The beams connecting to the column.
        **kwargs : dict
            Additional keyword arguments passed to the joint's constructor.

        Returns
        -------
        :class:`~compas_timber.connections.StekoJoint`
            The instance of the created joint.
        """
        joint = cls(steko_column, *steko_beams, **kwargs)

        system = StekoFastenerSystem()
        fastener = system.bind(joint.fastener_anchors, joint_type=joint.joint_type)

        # Only register the joint once binding its fastener has actually
        # succeeded - otherwise a failed bind (e.g. an unsupported column
        # topology) would leave a joint registered in the model with no
        # matching fastener.
        model.add_joint(joint)
        model.add_fastener(fastener, joint.beams)
        return joint

    @property
    def steko_column(self) -> Beam:
        return self.elements[-1] if self.elements else None

    @property
    def steko_beams(self) -> list[Beam]:
        return list(self.elements[:-1])

    @property
    def location(self) -> Point:
        point = Point(*intersection_line_line(self.steko_column.centerline, self.steko_beams[0].centerline)[0])
        return point

    @property
    def beams(self) -> list[Beam]:
        return [self.steko_column] + self.steko_beams

    @property
    def joint_type(self) -> int:
        """The :class:`StekoJointType` of this joint, derived from the number of beams connected to the column and,
        for two beams, whether they run straight through the column (linear) or meet it at an angle (angled)."""
        num_beams = len(self.steko_beams)
        if num_beams == 1:
            return StekoJointType.SOLO_BEAM
        if num_beams == 2:
            directions = [Vector.from_start_end(self.location, beam.centerline.midpoint).unitized() for beam in self.steko_beams]
            if TOL.is_close(directions[0].dot(directions[1]), -1.0):
                return StekoJointType.DOUBLE_LINEAR_BEAM
            return StekoJointType.DOUBLE_ANGLED_BEAM
        if num_beams == 3:
            return StekoJointType.TRIPLE_BEAM
        if num_beams == 4:
            return StekoJointType.QUADRUPLE_BEAM
        raise ValueError(f"StekoJoint does not support {num_beams} beams connected to the column.")

    @property
    def fastener_anchors(self):
        assert self.steko_column is not None, "steko_column must be defined to compute fastener anchors"
        assert self.steko_beams is not None, "steko_beams must be defined to compute fastener anchors"

        anchors = []

        for beam in self.steko_beams:
            # Building the slot anchors
            out_joint_beam_direction = Vector.from_start_end(self.location, beam.centerline.midpoint).unitized()
            plane_normal = Vector(*cross_vectors(out_joint_beam_direction, self.steko_column.frame.xaxis))
            plane = Plane(self.location, plane_normal)
            plane.translate(out_joint_beam_direction * self.steko_column.width / 2)

            front_plane = plane.copy()
            front_plane.translate(plane_normal * (beam.width / 2 - self.slot_padding - self.slot_width / 2))
            front_fame = Frame.from_plane(front_plane)
            anchor = FastenerAnchor(front_fame, AnchorKind.FACE, [self.steko_column, beam], role="slot_front")
            anchors.append(anchor)

            back_plane = plane.copy()
            back_plane.translate(plane_normal * -(beam.width / 2 - self.slot_padding - self.slot_width / 2))
            back_fame = Frame.from_plane(back_plane)
            anchor = FastenerAnchor(back_fame, AnchorKind.FACE, [self.steko_column, beam], role="slot_back")
            anchors.append(anchor)

            # The Dowels now
            # Go to the first plane
            plane.translate(Vector.Zaxis() * (-beam.height / 2 + 0.04))

            # The dowel grid's reach along the beam (base offset + 3 steps)
            # assumes a full-size beam. A short beam at a tight corner may
            # not have that much length available past the column face -
            # scale both down together so every dowel still lands on the
            # beam instead of missing it entirely.
            dowel_base_offset = 0.045
            dowel_step = 0.07
            available = beam.centerline.length / 2 - self.steko_column.width / 2 - 0.02
            max_reach = dowel_base_offset + 3 * dowel_step
            if 0 < available < max_reach:
                scale = available / max_reach
                dowel_base_offset *= scale
                dowel_step *= scale

            plane.translate(out_joint_beam_direction * dowel_base_offset)
            plane.translate(plane_normal * (beam.width / 2))
            for y in range(6):
                for x in range(4):
                    if y != 0 and y != 5 and x != 0 and x != 3:
                        continue
                    dowel_plane = plane.translated(Vector.Zaxis() * y * 0.08)
                    dowel_plane.translate(out_joint_beam_direction * x * dowel_step)
                    frame = Frame.from_plane(dowel_plane)
                    anchor = FastenerAnchor(frame, AnchorKind.AXIS, [beam], role="dowel")
                    anchors.append(anchor)

        return FastenerAnchors(anchors)

    def column_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.steko_column, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def beam_ref_side_index(self, beam, ref_beam):
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        self._extend_column_to_reach_location()
        for beam in self.steko_beams:
            ref_side_dict = beam_ref_side_incidence(beam, self.steko_column, ignore_ends=True)
            cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            cutting_plane = self.steko_column.ref_sides[cross_beam_ref_side_index]

            start, end = beam.extension_to_plane(cutting_plane)
            extension_tolerance = 0.01
            joint_id = self.guid
            beam.add_blank_extension(start + extension_tolerance, end + extension_tolerance, joint_id)

    def _extend_column_to_reach_location(self):
        """Extends steko_column's own blank so it actually reaches this joint's plates.

        A column's blank normally ends exactly at its story boundary, but the beams it
        connects to have their centerline dropped by half their height (see
        BeamGenerator), so the beam/column intersection point this joint is built around
        can land past the column's own material - most visibly at the bottom of a column
        segment that doesn't extend down into the story below. On top of that, a
        StekoSwordPlate's comb (see StekoFastener._bind_double_angled_beams and friends)
        reaches up to half the connected beam's own height above and below that location,
        not just the location point itself. StekoFastener's plates and dowels are
        positioned relative to that full reach regardless of whether the column's blank
        actually covers it: where it doesn't, the resulting Pocket volume pokes out past
        the column's blank on one side, which can corrupt (or entirely erase) the column's
        geometry instead of cutting a small, localized slot - the same failure mode
        Pocket.apply's start_depth guard already catches along the depth axis, but along
        the column's own length axis instead.
        """
        column = self.steko_column
        local_location = self.location.transformed(column.transformation_to_local())
        reach = max((beam.height for beam in self.steko_beams), default=0.0) / 2
        extension_tolerance = 0.01
        start_extension = max(0.0, -(local_location.x - reach) + extension_tolerance)
        end_extension = max(0.0, (local_location.x + reach) - column.length + extension_tolerance)
        if start_extension or end_extension:
            column.add_blank_extension(start_extension, end_extension, self.guid)

    def add_features(self):
        for beam in self.steko_beams:
            # Jack Rafter Cut
            plane = Plane.from_frame(self.steko_column.ref_sides[self.column_beam_ref_side_index(beam)])
            plane.normal *= -1
            jrc = JackRafterCutProxy.from_plane_and_beam(plane, beam)
            beam.add_feature(jrc)
            self.features.append(jrc)
