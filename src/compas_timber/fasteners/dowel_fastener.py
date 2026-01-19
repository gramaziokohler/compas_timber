from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.tolerance import Tolerance

from compas_timber.fasteners.fastener import Fastener

if TYPE_CHECKING:
    from compas_timber.fasteners.interface import Interface

TOL = Tolerance()


class Dowel(Fastener):
    """Class description"""

    def __init__(self, frame: Frame, height: float, diameter: float, interfaces: Optional[list[Interface]] = None):
        super().__init__(frame=frame, interfaces=interfaces)
        self.height = height
        self.diameter = diameter

    @property
    def __data__(self):
        return {"frame": self.frame.__data__, "height": self.height, "diameter": self.diameter, "interfaces": [interface.__data__ for interface in self.interfaces]}

    @classmethod
    def __from_data__(cls, data):
        frame = Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"])
        height = data["height"]
        diameter = data["diameter"]
        interfaces = [globals()[iface["type"]].__from_data__(iface) for iface in data.get("interfaces", [])]
        return cls(frame, height, diameter, interfaces)

    def compute_elementgeometry(self, include_interfaces=True):
        cylinder_frame = self.frame.copy()
        cylinder_frame.point += self.height / 2 * cylinder_frame.zaxis
        geometry = Cylinder(radius=self.diameter, height=self.height, frame=cylinder_frame)
        self._geometry = geometry

        if self.interfaces and include_interfaces:
            for interface in self.interfaces:
                geometry = interface.apply_to_fastener_geometry(geometry)

        geometry.transform(self.to_joint_transformation)

        return geometry
