from __future__ import annotations

from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line


class PlateHole:
    def __init__(self, frame: Frame, diameter: float, height: float, apply_drilling: bool = True, drilling_depth: float = 5, drilling_diameter: float = 2):
        self.frame = frame
        self.diameter = diameter
        self.height = height
        self.apply_drilling = apply_drilling
        self.drilling_depth = drilling_depth
        self.drilling_diameter = drilling_diameter

    def copy(self):
        return PlateHole(self.frame.copy(), self.diameter, self.height, self.apply_drilling, self.drilling_depth, self.drilling_diameter)

    @property
    def geometry(self):
        cylinder = Cylinder(radius=self.diameter / 2, height=self.height, frame=self.frame)
        cylinder.frame.point += cylinder.frame.zaxis * self.height / 2
        cylinder_brep = cylinder.to_brep()
        return cylinder_brep

    @property
    def drilling_line(self) -> Line:
        start = self.frame.point
        end = self.frame.point.translated(self.frame.zaxis * -self.drilling_depth)
        line = Line(start, end)
        return line
