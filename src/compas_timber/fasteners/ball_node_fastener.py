from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Optional

from compas import data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Sphere
from compas.geometry import Vector
from compas_model.elements import plate

from compas_timber.connections.ball_node import BallNodeJoint
from compas_timber.fabrication.jack_cut import JackRafterCut
from compas_timber.fabrication.jack_cut import JackRafterCutProxy
from compas_timber.fasteners.fastener import Fastener

if TYPE_CHECKING:
    from compas_timber.connections.ball_node import BallNodeFastener
    from compas_timber.elements.beam import Beam


@dataclass
class Rod:
    frame: Frame
    length: float
    beam: Beam
    plate_thickness: int = 10


class BallNodeFastener(Fastener):
    def __init__(self, frame: Frame, ball_diameter: float, rods: list[Rod], **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.ball_diameter = ball_diameter
        self.rods = rods
        self._node_point = None

    @property
    def __data__(self):
        data = {"frame": self.frame.__data__, "ball_diameter": self.ball_diameter, "interfaces": [interface.__data__ for interface in self.interfaces]}
        return data

    @classmethod
    def __from_data__(cls, data):
        frame = Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"])
        ball_diameter = data["ball_diameter"]
        interfaces = [globals()[iface["type"]].__from_data__(iface) for iface in data.get("interfaces", [])]
        return cls(frame=frame, ball_diameter=ball_diameter, interfaces=interfaces)

    @classmethod
    def from_joint(cls, joint: BallNodeJoint, ball_diameter: float, rods_length: float) -> BallNodeFastener:
        frame = Frame.worldXY()
        node_point = joint.node_point

        # compute the rods_frames:
        rods = []
        for beam in joint.beams:
            rod_direction = Vector.from_start_end(node_point, beam.centerline.midpoint)
            rod_direction.unitize()
            frame = Frame.from_plane(Plane(node_point, rod_direction))
            frame.point += ball_diameter / 2 * rod_direction

            rod = Rod(frame=frame, length=rods_length, beam=beam)
            rods.append(rod)

        ball_node_fastener = cls(frame=frame, ball_diameter=ball_diameter, rods=rods)
        return ball_node_fastener

    @property
    def ball_radius(self):
        return self.ball_diameter / 2

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
            cylinder_frame.point += cylinder.frame.zaxis * rod.length / 2
            cylinder = Cylinder(1.5, rod.length, frame=cylinder_frame)
            cylinder_geometry = Brep.from_cylinder(cylinder)
            geometry += cylinder_geometry

            # plate
            ref_side = min(rod.beam.ref_sides, key=lambda x: x.point.distance_to_point(rod.frame.point)).copy()
            height = rod.beam.height
            width = rod.beam.width
            ref_side.point = rod.frame.point + (rod.length - rod.plate_thickness / 2) * rod.frame.zaxis
            plate_geometry = Brep.from_box(Box(self.plate_thickness, width, height, frame=ref_side))
            geometry += plate_geometry

        geometry.transform(self.to_joint_transformation)

    def apply_processings(self, joint):
        for rod in self.rods:
            jack_rafter_cut = self._create_jack_rafter_cut_feature(rod)
            rod.beam.features.append(jack_rafter_cut)

    def _create_jack_rafter_cut_feature(self, rod):
        rafter_cut_frame = rod.frame.copy()
        rafter_cut_frame.point += rafter_cut_frame.zaxis * rod.length
        cutting_plane = Plane.from_frame(rafter_cut_frame)
        cutting_plane.normal *= -1
        try:
            jkrc = JackRafterCutProxy.from_plane_and_beam(cutting_plane, rod.beam)
            return jkrc
        except Exception as e:
            print(e)
            return None
