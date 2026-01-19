from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from attr.filters import include
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Sphere

from compas_timber.fasteners.ball_node_interface import BallNodeInterface
from compas_timber.fasteners.fastener import Fastener
from compas_timber.fasteners.hole_interface import HoleInterface
from compas_timber.fasteners.recess_interface import RecessInterface

if TYPE_CHECKING:
    from compas_timber.fasteners.interface import Interface


class BallNodeFastener2(Fastener):
    def __init__(self, frame: Frame, ball_diameter: float, interfaces: Optional[list[Interface]] = None, **kwargs):
        super().__init__(frame=frame, interfaces=interfaces, **kwargs)
        self.ball_diameter = ball_diameter

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

    @property
    def ball_radius(self):
        return self.ball_diameter / 2

    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        sphere = Sphere(radius=self.ball_diameter, frame=self.frame)
        geometry = Brep.from_sphere(sphere)
        geometry.transform(self.to_joint_transformation)
        if self.interfaces and include_interfaces:
            for interface in self.interfaces:
                geometry = interface.apply_to_fastener_geometry(geometry)
        return geometry
