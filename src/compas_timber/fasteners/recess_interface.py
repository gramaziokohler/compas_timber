from __future__ import annotations

from typing import TYPE_CHECKING

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame

from compas_timber.elements import TimberElement
from compas_timber.fabrication import Pocket
from compas_timber.fasteners.interface import Interface

if TYPE_CHECKING:
    from compas_timber.fabrication import BTLxProcessing


class RecessInterface(Interface):
    def __init__(self, frame: Frame, depth: float, width: float, height: float, **kwargs):
        super().__init__(frame, **kwargs)
        self.frame = frame
        self.depth = depth
        self.width = width
        self.height = height
        self.sub_fasteners = []

    @property
    def __data__(self):
        return {"type": "RecessInterface", "frame": self.frame.__data__, "depth": self.depth, "width": self.width, "height": self.height}

    @classmethod
    def __from_data__(cls, data):
        return cls(
            frame=Frame.__from_data__(data["frame"]),  # type: ignore
            depth=data["depth"],
            width=data["width"],
            height=data["height"],
        )

    def apply_to_fastener_geometry(self, fastener_geometry) -> Brep:
        return fastener_geometry

    def feature(self, element, transformation_to_joint) -> list[BTLxProcessing]:
        volume = Box(xsize=self.width, ysize=self.height, zsize=self.depth, frame=self.frame)
        volume.frame.point -= self.frame.zaxis * self.depth / 2
        volume = Brep.from_box(volume)
        volume.transform(transformation_to_joint)
        try:
            pocket = Pocket.from_volume_and_element(volume, element)
            self._logs.append(f"Pocket feature in RecessInterface succeded: {pocket}")
            return [pocket]
        except Exception as e:
            self._logs.append(f"Pocket feature in RecessInterface not succeded: {e}")
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
