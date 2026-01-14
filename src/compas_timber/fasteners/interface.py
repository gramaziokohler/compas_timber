from typing import Optional

from compas.data import Data
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Vector

from compas_timber.elements import TimberElement
from compas_timber.fabrication import BTLxProcessing
from compas_timber.fabrication import Drilling
from compas_timber.fasteners import Fastener


class Interface(Data):
    """Base class for interfaces"""

    def __init__(self, element: Optional[TimberElement] = None, features: Optional[list[BTLxProcessing]] = None):
        self.element = element
        self._features = []

    @property
    def features(self) -> list[BTLxProcessing]:
        return self._features

    def add_feature(self, feature: BTLxProcessing) -> None:
        self._features.append(feature)


# -------------------------------------------------


class HoleInterface:
    """Class description"""

    def __init__(self, frame: Frame, depth: float, diameter: float, direction: Optional[Vector] = None, element=None, **kwargs):
        self.frame = frame
        self.depth = depth
        self.diameter = diameter
        self.element = element

    @property
    def __data__(self):
        return {"frame": self.frame.__data__, "depth": self.depth, "diameter": self.diameter}

    @classmethod
    def __from_data__(cls, data):
        return cls(frame=Frame.__from_data__(data["frame"]), depth=data["depth"], diameter=data["diameter"])

    @property
    def features(self) -> list[BTLxProcessing]:
        try:
            start_point = self.frame.point
            end_point = self.frame.point + self.depth * -self.frame.zaxis
            line = Line(start_point, end_point)
            drilling = Drilling.from_line_and_element(line=line, element=self.element, diameter=self.diameter)
            print("Drilling succeded")
            return [drilling]
        except Exception:
            return []

    @property
    def shape(self):
        cylinder = Cylinder(radius=self.diameter * 0.5, height=self.depth, frame=self.frame)
        cylinder.frame.point += self.depth / 2 * self.frame.zaxis
        cylinder = Brep.from_cylinder(cylinder)
        return cylinder

    def get_features(self):
        return self.features

    def apply_to_fastener_geometry(self, fastener_geometry: Brep) -> Brep:
        print("frame from instance", self.frame)
        cylinder = Cylinder(radius=self.diameter * 0.5, height=self.depth, frame=self.frame)
        cylinder = Brep.from_cylinder(cylinder)
        fastener_geometry -= cylinder
        return fastener_geometry


# ------------------------------------------------------


class RecessInterfaces(Interface):
    def __init__(self, frame: Frame, depth: float, width: float, height: float, **kwargs):
        super().__init__(**kwargs)
        self.frame = frame
        self.depth = depth
        self.width = width
        self.height = height
