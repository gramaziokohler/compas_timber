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
        model.add_joint(joint)

        system = StekoFastenerSystem()
        fastener = system.bind(joint.fastener_anchors, joint_type=joint.joint_type)
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
            plane.translate(out_joint_beam_direction * (0.045))
            plane.translate(plane_normal * (beam.width / 2))
            for y in range(6):
                for x in range(4):
                    if y != 0 and y != 5 and x != 0 and x != 3:
                        continue
                    dowel_plane = plane.translated(Vector.Zaxis() * y * 0.08)
                    dowel_plane.translate(out_joint_beam_direction * x * 0.07)
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
        for beam in self.steko_beams:
            ref_side_dict = beam_ref_side_incidence(beam, self.steko_column, ignore_ends=True)
            cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            cutting_plane = self.steko_column.ref_sides[cross_beam_ref_side_index]

            start, end = beam.extension_to_plane(cutting_plane)
            extension_tolerance = 0.01
            joint_id = self.guid
            beam.add_blank_extension(start + extension_tolerance, end + extension_tolerance, joint_id)

    def add_features(self):
        for beam in self.steko_beams:
            # Jack Rafter Cut
            plane = Plane.from_frame(self.steko_column.ref_sides[self.column_beam_ref_side_index(beam)])
            plane.normal *= -1
            jrc = JackRafterCutProxy.from_plane_and_beam(plane, beam)
            beam.add_feature(jrc)
            self.features.append(jrc)
