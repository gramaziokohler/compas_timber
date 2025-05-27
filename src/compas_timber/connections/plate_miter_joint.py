from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Polygon
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import cross_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_polyline_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_segment_polyline
from compas.geometry import is_colinear_line_line
from compas.geometry import is_point_in_polygon_xy
from compas.geometry import Transformation
from compas.itertools import pairwise
from compas.tolerance import TOL

from .joint import Joint
from .joint import JointTopology
from .plate_joint import PlateJoint


class PlateMiterJoint(PlateJoint):
    """Creates a mitered edge plate-to-plate connection."""

    def __repr__(self):
        return "PlateMiterJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""

        assert self.main_plate
        assert self.cross_plate

        for polyline, plane in zip(self.main_outlines, self.cross_planes):
            for i, index in enumerate([self.main_segment_index-1, (self.main_segment_index+1)% len(self.main_plate.outline_a.lines)]):      #for each adjacent segment in the main plate outline
                seg = polyline.lines[index] # get the segment
                pt = intersection_line_plane(seg, plane)
                if pt:
                    if i == 0:
                        polyline[self.main_segment_index] = pt
                        if self.main_segment_index == 0:
                            polyline[-1] = pt
                    else:
                        polyline[self.main_segment_index+1] = pt
                        if self.main_segment_index+1 == len(polyline.lines):
                            polyline[0] = pt

            for polyline, plane in zip(self.cross_outlines, self.main_planes):
                for i, index in enumerate([self.cross_segment_index-1, (self.cross_segment_index+1)% len(self.cross_plate.outline_a.lines)]):      #for each adjacent segment in the main plate outline
                    seg = polyline.lines[index] # get the segment
                    pt = intersection_line_plane(seg, plane)
                    if pt:
                        if i == 0:
                            polyline[self.cross_segment_index] = pt
                            if self.cross_segment_index == 0:
                                polyline[-1] = pt
                        else:
                            polyline[self.cross_segment_index+1] = pt
                            if self.cross_segment_index+1 == len(polyline.lines):
                                polyline[0] = pt



