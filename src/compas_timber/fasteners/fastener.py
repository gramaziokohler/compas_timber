from __future__ import annotations

import uuid
from typing import Optional

from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation

from compas_timber.fabrication import Pocket


class Fastener:
    """
    This is the fastener and it is composed by parts.

    The fastener has to create the interactions between the elements.

    The fastener should be as independent as possible.

    Each part tells how the beam should be machined.

    It should never interact with a joint but it dies have one as reference.
    """

    def __init__(self, main_part, frame: Frame = Frame.worldXY(), target_frames: Optional[list[Frame]] = None):
        self.frame = Frame.worldXY()
        self.main_part = main_part
        self.interactions = []  # list of interactions tuple (child, parent)
        self.parts = [main_part]
        self.target_frames = target_frames
        self.guid = uuid.uuid4()

    @property
    def target_frames(self) -> list[Frame]:
        return self._target_frames

    @target_frames.setter
    def target_frames(self, value: Optional[list[Frame]]):
        if value is None:
            self._target_frames = []
            return
        if not isinstance(value, list):
            raise ValueError("target_frames should be a list of Frames.")
        else:
            self._target_frames = value

    @property
    def geometry(self):
        geometries = []
        for part in self.parts:
            part_geometry = part.geometry
            geometries.append(part_geometry)
        return geometries

    def copy(self) -> Fastener:
        new_fastener = Fastener(self.main_part)
        new_fastener.frame = self.frame.copy()
        new_fastener.parts = [part.copy() for part in self.parts]
        new_fastener.interactions = list(self.interactions)
        new_fastener.target_frames = list(self.target_frames)
        return new_fastener

    def add_child_part(self, part, parent):
        """
        Add a single part to the fastener.

        Parameters
        ----------

        part : Part
            The part to be added to the fastener.

        parent : list[Part]
            The parent of the part added.
        """
        self.parts.append(part)
        self.interactions.append((part, parent))

    def get_parent(self, part):
        """Return the parent of a specific part."""
        for interaction in self.interactions:
            if interaction[0] == part:
                return interaction[1]
        return None

    def get_children(self, part):
        """Return the children of the specific part."""
        children = []
        for interaction in self.interactions:
            if interaction[1] == part:
                children.append(interaction[0])
        return children

    def get_fastener_instances(self) -> list[Fastener]:
        fastener_instances = []
        for target_frame in self.target_frames:
            fastener_instance = self.copy()
            fastener_instance.frame = target_frame
            fastener_instance.target_frames = None

            transformation = Transformation.from_frame_to_frame(self.frame, target_frame)
            fastener_instance._update_parts_frame(transformation)

            fastener_instances.append(fastener_instance)
        return fastener_instances

    def apply_features(self, elements):
        for part in self.parts:
            part.apply_features(elements)

    def _update_parts_frame(self, transformation):
        for part in self.parts:
            part.frame = part.frame.transformed(transformation)


### ------------------


class PlateHole:
    def __init__(self, frame: Frame, diameter: float, height: float):
        self.frame = frame
        self.diameter = diameter
        self.height = height

    def copy(self):
        return PlateHole(self.frame.copy(), self.diameter, self.height)

    @property
    def geometry(self):
        cylinder = Cylinder(radius=self.diameter / 2, height=self.height, frame=self.frame)
        cylinder.frame.point += cylinder.frame.zaxis * self.height / 2
        cylinder_brep = cylinder.to_brep()
        return cylinder_brep


class RectangularPlate:
    def __init__(self, width: float, height: float, thickeness: float, frame: Frame = Frame.worldXY(), recess: float = 0, recess_offset: float = 0):
        self.width = width
        self.height = height
        self.thickness = thickeness
        self.holes = []
        self.frame = frame
        self.recess = recess
        self.recess_offset = recess_offset

    def copy(self) -> RectangularPlate:
        new_plate = RectangularPlate(self.width, self.height, self.thickness, self.frame.copy())
        new_plate.holes = [hole.copy() for hole in self.holes]
        return new_plate

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, value):
        if not isinstance(value, Frame):
            raise ValueError("frame should be a Frame object.")
        for hole in self.holes:
            hole.frame.transform(Transformation.from_frame_to_frame(self._frame, value))
        self._frame = value

    @property
    def geometry(self):
        box_brep = self.blank_geometry
        for hole in self.holes:
            box_brep -= hole.geometry
        return box_brep

    @property
    def blank_geometry(self):
        box = Box(self.width, self.height, self.thickness, frame=self.frame)
        box.frame.point += self.frame.zaxis * self.thickness / 2
        box_brep = box.to_brep()
        return box_brep

    def add_hole(self, point: Point, diameter: float):
        hole_frame = self.frame.copy()
        hole_frame.point = point
        hole = PlateHole(hole_frame, diameter, self.thickness)
        self.holes.append(hole)

    def add_hole_grid(self, nx: int, ny: int, border_padding: float, diameter: float):
        for ix in range(nx):
            for iy in range(ny):
                x = self.frame.point.x + border_padding + ix * (self.width - 2 * border_padding) / (nx - 1)
                x -= self.width / 2

                y = self.frame.point.y + border_padding + iy * (self.height - 2 * border_padding) / (ny - 1)
                y -= self.height / 2

                self.add_hole(Point(x, y, 0), diameter)

    def apply_features(self, elements):
        for element in elements:
            geo = self.blank_geometry
            geo.translate(-self.frame.zaxis * 3)
            pocket = Pocket.from_volume_and_element(geo, element)
            element.add_feature(pocket)
            print(pocket.start_depth)


class Dowel:
    def __init__(self, diameter: float, length: float, frame: Optional[Frame]):
        self.frame = Frame.worldXY()
        self.diameter = diameter
        self.length = length
