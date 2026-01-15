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

    def __init__(self, frame: Frame, height: float, radius: float, interfaces: Optional[list[Interface]]):
        super().__init__(frame=frame)
        self.height = height
        self.radius = radius
        self.interfaces = []
        self._shape = None

    def place_instances(self, frames: list[Frame]) -> None:
        pass

    def compute_elementgeometry(self, include_interfaces=True):
        cylinder_frame = self.frame.point + self.heigth / 2 * self.frame.zaxis
        geometry = Cylinder(radius=self.radius, height=self.height, frame=cylinder_frame)
        self._geometry = geometry

        if self.interfaces and include_interfaces:
            for interface in self.interfaces:
                geometry = interface.apply_to_fastener_geometry(geometry)

        geometry.transform(self.to_joint_transformation)

        return geometry
