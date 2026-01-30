from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Sphere
from compas.geometry import Vector

from compas_timber.connections.joint import Joint
from compas_timber.fabrication.jack_cut import JackRafterCutProxy
from compas_timber.fasteners.fastener import Fastener

if TYPE_CHECKING:
    from compas_timber.connections.ball_node import BallNodeFastener
    from compas_timber.connections.ball_node import BallNodeJoint
    from compas_timber.elements.beam import Beam


@dataclass
class Rod:
    frame: Frame
    length: float
    beam: Beam
    plate_thickness: int = 3


class BallNodeFastener(Fastener):
    def __init__(self, frame: Frame, ball_diameter: float, rods: list[Rod], **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.ball_diameter = ball_diameter
        self.rods = rods

    @classmethod
    def from_joint(cls, joint: BallNodeJoint, ball_diameter: float, rods_length: float) -> BallNodeFastener:
        # creation of the base_fastener everything in local space!
        frame = Frame.worldXY()
        node_point = joint.node_point
        # compute the rods_frames:
        rods = []
        for beam in joint.beams:
            rod_direction = Vector.from_start_end(node_point, beam.centerline.midpoint)
            rod_direction.unitize()
            rod_frame = Frame.from_plane(Plane(node_point, rod_direction))
            rod_frame.point = frame.point + (ball_diameter / 2 * rod_direction)  # at the local space
            rod = Rod(frame=rod_frame, length=rods_length, beam=beam)
            rods.append(rod)
        ball_node_fastener = cls(frame=frame, ball_diameter=ball_diameter, rods=rods)
        return ball_node_fastener

    @property
    def ball_radius(self) -> float:
        return self.ball_diameter / 2

    def copy(self) -> BallNodeFastener:
        return BallNodeFastener(
            frame=self.frame.copy(),
            ball_diameter=self.ball_diameter,
            rods=[Rod(frame=rod.frame.copy(), length=rod.length, beam=rod.beam, plate_thickness=rod.plate_thickness) for rod in self.rods],
        )

    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        """Compute the geometry of the fastener element.

        Parameters
        ----------
        include_interfaces : bool, optional
            Whether to include the interfaces in the geometry.

        Returns
        -------
        Brep
            The geometry of the fastener element.
        """
        sphere = Sphere(radius=self.ball_diameter, frame=self.frame)
        geometry = Brep.from_sphere(sphere)

        # add rods geometry
        for rod in self.rods:
            # rod
            cylinder_frame = rod.frame.copy()
            cylinder_frame.point += cylinder_frame.zaxis * rod.length / 2
            cylinder = Cylinder(1.5, rod.length, frame=cylinder_frame)
            cylinder_geometry = Brep.from_cylinder(cylinder)
            geometry += cylinder_geometry

            # plate
            height = rod.beam.height
            width = rod.beam.width
            plate_frame = rod.beam.frame.copy()
            plate_frame.point = rod.frame.point + (rod.length - rod.plate_thickness / 2) * rod.frame.zaxis
            plate_geometry = Brep.from_box(Box(rod.plate_thickness, width, height, frame=plate_frame))
            geometry += plate_geometry

        geometry.transform(self.to_joint_transformation)

        return geometry

    def apply_processings(self, joint: Joint) -> None:
        """
        Applies the necessary processing features to the beams connected by the ball node fastener.

        Parameters
        ----------
        joint : :class:`compas_timber.connections.BallNodeJoint`
            The joint to which the fastener is applied.

        """
        for rod in self.rods:
            jack_rafter_cut = self._create_jack_rafter_cut_feature(rod)
            rod.beam.features.append(jack_rafter_cut)

    def _create_jack_rafter_cut_feature(self, rod) -> Optional[JackRafterCutProxy]:
        rafter_cut_frame = rod.frame.copy()
        rafter_cut_frame.point += rafter_cut_frame.zaxis * rod.length
        # rods frame anre in local space, transform it to global
        rafter_cut_frame.transform(self.to_joint_transformation)
        cutting_plane = Plane.from_frame(rafter_cut_frame)
        cutting_plane.normal *= -1
        try:
            jkrc = JackRafterCutProxy.from_plane_and_beam(cutting_plane, rod.beam)
            return jkrc
        except Exception as e:
            print(e)
            return None
