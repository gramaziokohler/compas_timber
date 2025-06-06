# TODO: move this to compas_timber.fasteners
from compas.data import Data
from compas.itertools import pairwise
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import Brep
from compas.geometry import Curve
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import intersection_segment_plane

from compas_timber.elements.timber import TimberElement
from compas_timber.fabrication import Drilling
from compas_timber.utils import intersection_line_beam_param


class LinearService(TimberElement):
    """
    A class to represent linear MEP elements (electrical, pipes, round ducting).

    Parameters
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    Attributes
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    """

    def __init__(self, polyline=None, diameter = None, frame=None, **kwargs):
        super(LinearService, self).__init__(**kwargs)
        self.polyline = polyline
        self.diameter = diameter
        self.interfaces = []
        self.frame = frame
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "LinearService(frame={!r}, name={})".format(self.frame, self.name)

    def __str__(self):
        # type: () -> str
        return "<LinearService {}>".format(self.name)

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame

    @property
    def is_linear_service(self):
        return True

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    @property
    def __data__(self):
        return {
            "polyline": self.polyline,
            "diameter": self.diameter,
            "frame": self.frame,
            "interfaces": self.interfaces,
        }
    
    def apply_drilling(self, element):
        """Apply drilling features to the element."""
        for segment in pairwise(self.polyline):
            pts, _ = intersection_segment_element_param(segment, element)
            if pts:
                element.add_feature(Drilling.from_line_and_element(Line(*pts), element, self.diameter))

    def compute_geometry(self):
        """returns the geometry of the fastener in the model"""
        return Brep.from_pipe(self.polyline, self.diameter/2)



def intersection_segment_element_param(segment, element, ignore_ends=False):
    """Get the intersection of a line with a beam in the XY plane and the corresponding ref_face_indices.

    Parameters
    ----------
    line : :class:`~compas.geometry.Line`
        The line to intersect with the beam.
    beam : :class:`~compas_timber.geometry.Beam`
        The beam to intersect with the line.
    ignore_ends : bool, optional
        If True, the intersection with the beam ends is ignored. Default is False.

    Returns
    -------
    list of :class:`~compas.geometry.Point`
        list of intersection points.
    list of int
        list of indices of the reference faces of the beam that the intersection points lie on.

    """

    sides = element.ref_sides[:4] if ignore_ends else element.ref_sides
    pts = []
    ref_side_indices = []
    for i, face in enumerate(sides):
        intersection = intersection_segment_plane(segment, Plane.from_frame(face))
        if intersection:
            int_pt = Point(*intersection)
            intersection_uv = int_pt.transformed(Transformation.from_frame_to_frame(face, Frame.worldXY()))
            if intersection_uv[0] >= 0 and intersection_uv[0] < element.side_as_surface(i).xsize and intersection_uv[1] > 0 and intersection_uv[1] < element.side_as_surface(i).ysize:
                pts.append(intersection)
                ref_side_indices.append(i)
    return [Point(*coords) for coords in pts], ref_side_indices