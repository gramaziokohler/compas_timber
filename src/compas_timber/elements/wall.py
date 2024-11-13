import statistics

import compas.geometry
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import bounding_box
from compas.geometry import Brep

from .timber import TimberElement


class Wall(TimberElement):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = super(Wall, self).__data__
        data["outline"] = self.outline
        data["openings"] = self.openings
        data["thickness"] = self.thickness
        return data

    def __init__(self, outline, thickness, openings=None, frame=None, **kwargs):
        # type: (compas.geometry.Polyline, float, list[Polyline], Frame, dict) -> None
        super(Wall, self).__init__(frame=frame or Frame.worldXY(), **kwargs)
        self.outline = outline
        self.thickness = thickness
        self.openings = openings or []

        if not outline.is_closed:
            raise ValueError("Outline is not closed.")
        if len(self.outline) != 5:
            raise ValueError("Wall outline must have 4 segments.")

    @property
    def is_wall(self):
        return True

    @property
    def is_group_element(self):
        return True

    @property
    def origin(self):
        assert self.frame
        return self.frame.point.copy()

    @property
    def baseline(self):
        # type: () -> Line
        assert self.frame
        # TODO: find the bottom line of wall. don't love this, but it works for now. might be fair to rely on a consistent order of points
        z_means = {statistics.mean([line.start.z, line.end.z]): line for line in self.outline.lines}
        return z_means[min(z_means.keys())]

    def compute_geometry(self, _=False):
        assert self.frame

        extrusion_vector = self.frame.zaxis * self.thickness
        return Brep.from_extrusion(self.outline, extrusion_vector)

    def compute_aabb(self, inflate_by=0.1):
        obb = self.compute_obb(inflate_by)
        return Box.from_bounding_box(bounding_box(obb.points))

    def compute_obb(self, inflate_by=0.0):
        assert self.frame
        points = self.outline.points
        # TODO: this is more like obb than aabb
        box_corners = [
            points[0],
            points[1],
            points[1] + self.frame.zaxis * self.thickness,
            points[0] + self.frame.zaxis * self.thickness,
            points[3],
            points[2],
            points[2] + self.frame.zaxis * self.thickness,
            points[3] + self.frame.zaxis * self.thickness,
        ]
        box = Box.from_bounding_box(box_corners)
        box.xsize += inflate_by
        box.ysize += inflate_by
        box.zsize += inflate_by
        return box

    def __repr__(self):
        return "Wall({}, {:.3f}, {:.3f}, {:.3f})".format(self.frame, self.outline, self.thickness, self.openings)

    @classmethod
    def from_box(cls, box):
        # type: (Box) -> Wall
        boxframe = box.frame.copy()
        origin = boxframe.point
        origin -= boxframe.xaxis * box.xsize * 0.5
        origin -= boxframe.yaxis * box.ysize * 0.5
        origin -= boxframe.zaxis * box.zsize * 0.5
        return cls(box.xsize, box.ysize, box.zsize, frame=boxframe)

    @classmethod
    def from_baseline(cls, baseline, thickness, height, y_vector):
        # TODO: baseline is x_axis, y_vector must be perpendicular to baseline
        raise NotImplementedError
