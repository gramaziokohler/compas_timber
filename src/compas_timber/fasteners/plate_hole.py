from __future__ import annotations

from typing import Optional

from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line


class PlateHole:
    """
    Describes a hole in a fastener plate.
    It has a diameter, a height, and a frame that describes its position and orientation in space relative to
    the frame of the fastener.
    It can appply `Drilling` fabrication process to the beam, in which case it has a drilling depth and diameter.


    Parameters
    ----------
    frame : Frame
        The frame of the hole, describing its position and orientation in space relative to the frame of the fastener.
    diameter : float
        The diameter of the hole.
    height : float
        The height of the hole, i.e. the thickness of the plate.
    apply_drilling : bool, optional
        Whether to apply a drilling process to the beam, by default True.
    drilling_depth : float, optional
        The depth of the drilling process to be applied to the beam, by default 5.
    drilling_diameter : float, optional
        The diameter of the drilling process to be applied to the beam, by default is the same as the diameter.

    """

    def __init__(
        self, frame: Frame, diameter: float, height: float, apply_drilling: bool = True, drilling_depth: Optional[float] = None, drilling_diameter: Optional[float] = None
    ):
        self.frame = frame
        self.diameter = diameter
        self.height = height
        self.apply_drilling = apply_drilling
        self.drilling_depth = drilling_depth if drilling_depth is not None else 5
        self.drilling_diameter = drilling_diameter if drilling_diameter is not None else diameter

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
