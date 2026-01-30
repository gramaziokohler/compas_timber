from __future__ import annotations

from typing import Optional

from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.tolerance import Tolerance

from compas_timber.elements import TimberElement
from compas_timber.fabrication import Drilling
from compas_timber.fasteners.fastener import Fastener

TOL = Tolerance()


class Dowel(Fastener):
    """Class description"""

    def __init__(self, frame: Frame, height: float, diameter: float, head_bias: Optional[float] = None, processings: bool = False, **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.height = height
        self.diameter = diameter
        self.head_bias = head_bias
        self.processings = processings

    @property
    def __data__(self):
        return {"frame": self.frame.__data__, "height": self.height, "diameter": self.diameter, "head_bias": self.head_bias, "processings": self.processings}

    @classmethod
    def __from_data__(cls, data):
        frame = Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"])
        height = data["height"]
        diameter = data["diameter"]
        head_bias = data["head_bias"]
        processings = data["processings"]

        return cls(frame, height, diameter, head_bias=head_bias, processings=processings)

    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        self.frame.transform(self.to_joint_transformation)
        cylinder_frame = self.frame.copy()
        cylinder_frame.point -= self.height / 2 * cylinder_frame.zaxis
        if self.head_bias:
            print(self.head_bias)
            cylinder_frame.point += self.head_bias * cylinder_frame.zaxis
        geometry = Cylinder(radius=self.diameter / 2, height=self.height, frame=cylinder_frame)
        self._geometry = geometry
        # geometry.transform(self.to_joint_transformation)
        geometry = Brep.from_cylinder(geometry)
        return geometry

    def apply_processings(self, joint) -> Optional[Brep]:
        if not self.processings:
            return
        for element in joint.elements:
            if not isinstance(element, TimberElement):
                continue
            drilling = self._create_drilling_feature(element)
            element.features.append(drilling)

    def _create_drilling_feature(self, element: TimberElement) -> Optional[Drilling]:
        start_point = self.frame.point + self.frame.zaxis * 0.01
        end_point = self.frame.point + self.height * -self.frame.zaxis
        line = Line(start_point, end_point)
        line.transform(self.to_joint_transformation)

        try:
            drilling = Drilling.from_line_and_element(line=line, element=element, diameter=self.diameter)
            return drilling
        except Exception as e:
            print(e)
