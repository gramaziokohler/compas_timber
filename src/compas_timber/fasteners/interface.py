from typing import Optional

from compas.data import Data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import project_point_plane

from compas_timber.elements import TimberElement
from compas_timber.fabrication import BTLxProcessing
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import Pocket
from compas_timber.fasteners import Fastener


class Interface(Data):
    """Base class for interfaces"""

    def __init__(self, kwargs):
        self.kwargs = kwargs

    @classmethod
    def __from_data__(cls, data):
        type_tag = data.get("type")
        if not type_tag:
            return
        sub = cls._registry.get(type_tag.lower())
        if not sub:
            raise ValueError(f"Unknown Interface type '{type_tag}' in data: {data}")
        ctor = getattr(sub, "__from_data__", getattr(sub, "from_data", None))
        if not ctor:
            raise TypeError(f"Registered Interface class {sub} has no from-data constructor")
        return ctor(data)

    @property
    def features(self) -> list[BTLxProcessing]:
        return self._features

    def add_feature(self, feature: BTLxProcessing) -> None:
        self._features.append(feature)


# -------------------------------------------------


class HoleInterface(Interface):
    """Class description"""

    def __init__(self, frame: Frame, depth: float, diameter: float, direction: Optional[Vector] = None, element=None, **kwargs):
        super().__init__(kwargs)
        self.frame = frame
        self.depth = depth
        self.diameter = diameter
        self.element = element

    @property
    def __data__(self):
        return {"type": "HoleInterface", "frame": self.frame.__data__, "depth": self.depth, "diameter": self.diameter}

    @classmethod
    def __from_data__(cls, data):
        interface = cls(frame=Frame.__from_data__(data["frame"]), depth=data["depth"], diameter=data["diameter"])
        return interface

    @property
    def shape(self):
        cylinder = Cylinder(radius=self.diameter * 0.5, height=self.depth, frame=self.frame)
        cylinder.frame.point += self.depth / 2 * self.frame.zaxis
        cylinder = Brep.from_cylinder(cylinder)
        return cylinder

    def apply_to_fastener_geometry(self, fastener_geometry) -> Brep:
        cylinder = Cylinder(radius=self.diameter * 0.5, height=self.depth, frame=self.frame)
        cylinder = Brep.from_cylinder(cylinder)
        fastener_geometry -= cylinder
        return fastener_geometry

    def feature(self, element, transformation_to_joint) -> Optional[BTLxProcessing]:
        start_point = self.frame.point + self.frame.zaxis * 0.01
        end_point = self.frame.point + self.depth * -self.frame.zaxis
        line = Line(start_point, end_point)
        line.transform(transformation_to_joint)
        try:
            drilling = Drilling.from_line_and_element(line=line, element=element, diameter=self.diameter)
            return [drilling], line
        except Exception as e:
            print("Drilling not succeded: ", e)
            return [], None

    def apply_features_to_elements(self, joint, transformation_to_joint):
        lines = []
        for element in joint.elements:
            if not isinstance(element, TimberElement):
                continue
            processings, line = self.feature(element, transformation_to_joint)
            lines.append(line)
            if processings:
                element.features.extend(processings)
            else:
                continue
        return lines


# ------------------------------------------------------


class RecessInterface(Interface):
    def __init__(self, frame: Frame, depth: float, width: float, height: float, **kwargs):
        super().__init__(kwargs)
        self.frame = frame
        self.depth = depth
        self.width = width
        self.height = height

    @property
    def __data__(self):
        return {"type": "RecessInterface", "frame": self.frame.__data__, "depth": self.depth, "width": self.width, "height": self.height}

    @classmethod
    def __from_data__(cls, data):
        return cls(frame=Frame.__from_data__(data["frame"]), depth=data["depth"], width=data["width"], height=data["height"])

    def apply_to_fastener_geometry(self, fastener_geometry) -> Brep:
        return fastener_geometry

    def feature(self, element, transformation_to_joint) -> Optional[BTLxProcessing]:
        volume = Box(xsize=self.width, ysize=self.height, zsize=self.depth, frame=self.frame)
        volume.frame.point -= self.frame.zaxis * self.depth / 2
        volume = Brep.from_box(volume)
        volume.transform(transformation_to_joint)
        try:
            pocket = Pocket.from_volume_and_element(volume, element)
            print(pocket)
            return [pocket]
        except Exception as e:
            print("Pocket not succeded. ", e)
            return []

    def apply_features_to_elements(self, joint, transformation_to_joint):
        for element in joint.elements:
            if not isinstance(element, TimberElement):
                continue
            processings = self.feature(element, transformation_to_joint)
            if processings:
                element.features.extend(processings)
            else:
                continue

    def volume(self, element, transformation_to_joint):
        volume = Box(xsize=self.width, ysize=self.height, zsize=self.depth, frame=self.frame)
        volume.frame.point -= self.frame.zaxis * self.depth / 2
        volume = Brep.from_box(volume)
        volume.transform(transformation_to_joint)
        return volume
