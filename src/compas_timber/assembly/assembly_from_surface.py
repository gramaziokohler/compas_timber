from ast import parse
from calendar import c
from email import header
import math
from compas.geometry import Brep
from compas_timber.parts import Beam
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import offset_line
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import bounding_box_xy
from compas.geometry import transform_points
from compas.geometry import matrix_from_frame_to_frame
from compas.geometry import intersection_line_segment
from compas.geometry import intersection_line_line
from compas.geometry import intersection_segment_segment
from compas.geometry import closest_point_on_segment
from compas.geometry import bounding_box
from compas.geometry import Point
from compas.geometry import Line


class SurfaceAssembly(object):
    def __init__(
        self,
        surface,
        beam_width,
        beam_height,
        stud_spacing,
        z_axis = None,
        sheeting_thickness=None,
        sheeting_inside=None,
        lintel_posts=True,
    ):
        """Create a timber assembly from a surface.

        Parameters
        ----------
        surface : :class:`compas.geometry.Surface`
            The surface to create the assembly from. must be planar.
        beam_height : float
            The height of the beams aka thickness of wall cavity normal to the surface.
        beam_width : float
            The width of the beams.
        stud_spacing : float
            The spacing between the studs.
        z_axis : :class:`compas.geometry.Vector`, optional
            Determines the orientation of the posts inside the frame.
            Default is ``Vector.Zaxis``.
        sheeting_thickness : :class:`compas.geometry.Surface`, optional
            The thickness of sheeting applied to the assembly. Applies to both sides of assembly unless sheeting_inside is specified.
            Default is ``None``.
        sheeting_inside : :class:`compas.geometry.Surface`, optional
            The inside sheeting thickness of the assembly.
            Default is ``None``.
        lintel_posts : bool, optional
            Add lintel posts to the assembly.
            Default is ``True``.

        Returns
        -------
        :class:`compas_timber.assembly.TimberAssembly`
        """

        # if not isinstance(surface, Brep):
        #     raise TypeError('Expected a compas.geometry.Surface, got: {}'.format(type(surface)))
        # if not isinstance(z_axis, Vector):
        #     raise TypeError('Expected a compas.geometry.Vector, got: {}'.format(type(z_axis)))
        # if stud_spacing is not None and not isinstance(stud_spacing, float):
        #     raise TypeError('Expected a float, got: {}'.format(type(stud_spacing)))
        # if sheeting_thickness is not None and not isinstance(sheeting_thickness, float):
        #     raise TypeError('Expected a float, got: {}'.format(type(sheeting_thickness)))
        # if sheeting_inside is not None and not isinstance(sheeting_inside, float):
        #     raise TypeError('Expected a float, got: {}'.format(type(sheeting_inside)))
        # if not isinstance(lintel_posts, bool):
        #     raise TypeError('Expected a bool, got: {}'.format(type(lintel_posts)))

        self.surface = surface
        self.beam_width = beam_width
        self.beam_height = beam_height
        self.header_height = 25
        self.stud_spacing = stud_spacing
        self.z_axis = z_axis or Vector.Zaxis()
        self.sheeting_thickness = sheeting_thickness
        self.sheeting_inside = sheeting_inside
        self.lintel_posts = lintel_posts
        self._normal = None
        self.outer_polyline = None
        self.inner_polylines = []
        self.test_points = []
        self.edges = []
        self._frame = None
        self._panel_length = None
        self._panel_height = None
        self.jack_stud_indices = []
        self.sill_indices = []
        self.header_indices = []
        self.edge_stud_indices = []
        self.plate_indices = []
        self.outer_segments = []
        self.elements = []


        self.king_studs = []
        self.studs = []

        self.parse_loops()
        self.process_outline()
        self.make_windows()
        self.trim_studs()



    @property
    def centerlines(self):
        centerlines = {}
        centerlines["edge_studs"] = self.edge_studs
        centerlines["headers"] = self.headers
        centerlines["plates"] = self.plates
        centerlines["sills"] = self.sills
        centerlines["headers"] = self.headers
        centerlines["jack_studs"] = self.jack_studs
        centerlines["king_studs"] = self.king_studs
        centerlines["studs"] = self.studs
        return centerlines

    @property
    def beams(self):
        beams = []
        for key, value in self.centerlines.items():
            for line in value:
                width = self.header_height(line) if key == "headers" else self.beam_width
                beam = Beam.from_centerline(
                    centerline=line, width=width, height=self.beam_height, z_vector=self.normal
                )
                beam.attributes["category"] = str(key)
                beams.append(beam)
        return beams

    @property
    def points(self):
        return self.base_outline.points

    @property
    def normal(self):
        if not self._normal:
            self._normal = self.surface.native_brep.Faces[0].NormalAt(0.5, 0.5)
        return self._normal

    @property
    def panel_length(self):
        if not self._panel_length:
            _ = self.frame
        return self._panel_length

    @property
    def panel_height(self):
        if not self._panel_height:
            _ = self.frame
        return self._panel_height

    @property
    def frame(self):
        if not self._frame:
            self._frame, self._panel_length, self._panel_height = get_frame(self.points, self.normal, self.z_axis)
        return self._frame

    @property
    def jack_studs(self):
        curves = [self.segments[i] for i in self.jack_stud_indices]
        curves.extend([window.jack_studs for window in self.windows])
        return curves

    @property
    def sills(self):
        curves = [self.segments[i] for i in self.sill_indices]
        curves.extend([window.sills for window in self.windows])
        return curves

    @property
    def headers(self):
        curves = [self.segments[i] for i in self.header_indices]
        curves.extend([window.headers for window in self.windows])
        return curves

    @property
    def plates(self):
        return [self.segments[i] for i in self.plate_indices]



    def parse_loops(self):
        for loop in self.surface.loops:
            polyline_points = []
            for i, edge in enumerate(loop.edges):
                if not edge.is_line:
                    raise ValueError("function only supprorts polyline edges")
                if edge.start_vertex.point in [
                    loop.edges[i - 1].start_vertex.point,
                    loop.edges[i - 1].end_vertex.point,
                ]:
                    polyline_points.append(edge.start_vertex.point)
                else:
                    polyline_points.append(edge.end_vertex.point)
            polyline_points.append(polyline_points[0])
            if loop.is_outer:
                self.base_outline = Polyline(polyline_points)
                polyline = Polyline(polyline_points)
                polyline.translate(self.normal * 0.5 * self.beam_height)
                self.outer_polyline = polyline

            else:
                polyline = Polyline(polyline_points)
                polyline.translate(self.normal * 0.5 * self.beam_height)
                self.inner_polylines.append(polyline)



    def process_outline(self):
        interior_indices = self.get_interior_segment_indices(self.outer_polyline)
        for i, segment in enumerate(self.outer_polyline.lines):
            print(segment)
            self.outer_segments.append(segment)
            if i in interior_indices:
                print("interior")
                if (
                angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):

                    self.jack_stud_indices.append(i)
                else:
                    self.header_indices.append(i)
            else:
                print(self.z_axis)
                if (
                    angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                    or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):
                    self.edge_stud_indices.append(i)
                else:
                    self.plate_indices.append(i)
        self.offset_outline()


    def get_interior_segment_indices(self, polyline):
        interior = []
        interior_corners = self.get_interior_corner(polyline)
        for i in interior_corners:
            interior.append(polyline.lines[i-1])
            interior.append(polyline.lines[i])
        interior = set(interior)
        return interior


    def get_interior_corner(self, polyline):
        out = []
        for index in range(len(polyline)):
            if index == 0:
                angle = angle_vectors_signed(
                    polyline[-1] - polyline[0], polyline[1] - polyline[0], self.normal, deg=True
                )
            elif index == len(polyline) - 1:
                angle = angle_vectors_signed(
                    polyline[-2] - polyline[-1], polyline[0] - polyline[-1], self.normal, deg=True
                )
            else:
                angle = angle_vectors_signed(
                    polyline[index - 1] - polyline[index], polyline[index + 1] - polyline[index], self.normal, deg=True
                )
            if angle > 0:
                out.append(index)
        return out


    def make_windows(self):
        for polyline in self.inner_polylines:
            self.windows.append(Window(polyline, self.frame, self.beam_width, self.beam_width, self.header_height))


    def offset_outline(self):
        offset_segs = []
        for i, seg in enumerate(self.outer_segments):
            if i in self.header_indices:
                offset_segs.append(Line(offset_line(seg, self.header_height/2, self.normal)))
            elif i in self.sill_indices:
                offset_segs.append(Line(offset_line(seg, self.sill_height/2, self.normal)))
            elif i in self.jack_stud_indices:
                offset_segs.append(Line(offset_line(seg, self.beam_width/2, self.normal)))
                self.king_studs.append(offset_line(seg, self.beam_width, self.normal))
            else:
                ln = offset_line(seg, self.beam_width/2, self.normal)
                offset_segs.append(Line(ln[0], ln[1]))
            offset_pline_pts = []
            print(offset_segs)
            for i, seg in enumerate(offset_segs):
                point = intersection_line_line(seg, offset_segs[i - 1], 0.01)[0]
                print("point = ", point)
                offset_pline_pts.append(point)
            print("pts = ", offset_pline_pts)
            offset_pline_pts.append(offset_pline_pts[0])
            self.segments = Polyline(offset_pline_pts).lines


    def trim_studs(self):
        self.generate_studs_lines()
        self.trim_jack_studs()
        self.trim_king_studs()
        self.trim_studs()



    def generate_studs_lines(self):
        x_position = self.stud_spacing + (self.beam_width / 2.0)
        studs = []
        while x_position < self.panel_length:
            start_point = Point(x_position, 0, 0)
            start_point.transform(matrix_from_frame_to_frame(Frame.worldXY(), self.frame))
            start_point.translate(self.normal * 0.5 * self.beam_height)
            studs.append(Line.from_point_and_vector(start_point, self.z_axis * self.panel_height))
            x_position += self.stud_spacing
        self.studs = studs


    def get_intersections(self, line, *line_lists_to_intersect):
        intersections = []
        dots = []
        for line_list in line_lists_to_intersect:
            for line_to_intersect in line_list:
                point = intersection_line_segment(line, line_to_intersect, 0.01)[0]
                if point:
                    intersections.append(point)
        if len(intersections) > 1:
            intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
            dots = [
                dot_vectors(Vector.from_start_end(line.start, x), self.z_axis) / line.length for x in intersections
            ]
        return intersections, dots



    def trim_jack_studs(self):
        new_lines = []
        for line in self.jack_studs:
            pts = offset_line(line, self.beam_width, self.normal)
            self.king_studs.append(Line(pts[0], pts[1]))
            if dot_vectors(line.direction, self.z_axis) < 0:
                line = Line(line.end, line.start)
            intersections, dots = self.get_intersections(line, self.plates, self.headers)
            if len(intersections) > 1:
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                    if abs(dot - 1) < 0.01:
                        top = intersections[i]
                        break
                if not bottom:
                    bottom = line.start
                if not top:
                    top = line.end
            new_lines.append(Line(bottom, top))
        self.jack_studs = new_lines


    def trim_king_studs(self):
        new_lines = []
        for line in self.king_studs:
            if dot_vectors(line.direction, self.z_axis) < 0:
                line = Line(line.end, line.start)
            intersections, dots = self.get_intersections(line, self.plates, self.headers, self.sills)
            if len(intersections) > 1:
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                    if dot > 1:
                        top = intersections[i]
                        break
                if not bottom:
                    bottom = line.start
                if not top:
                    top = line.end
            new_lines.append(Line(bottom, top))

        self.king_studs = new_lines


    def trim_studs(self):
        new_lines = []
        for line in self.studs:
            if dot_vectors(line.direction, self.z_axis) < 0:
                line = Line(line.end, line.start)
            intersections, _ = self.get_intersections(line, self.plates, self.headers, self.sills)
            while len(intersections) > 1:
                top = intersections.pop()
                bottom = intersections.pop()
                new_lines.append(Line(bottom, top))

        self.studs = new_lines


class Window(object):
    def __init__(self, outline, frame, stud_width, sill_height, header_height = None):
        self.outline = outline
        self._sill_height = sill_height
        self._header_height = header_height
        self.stud_width = stud_width
        self.panel_frame = frame

        self.z_axis = frame.yaxis
        self.normal = frame.zaxis
        self.jack_stud_indices = []
        self.sill_indices = []
        self.header_indices = []
        self.segments = []
        self._length = None
        self._height = None
        self._normal = None
        self._frame = None
        self._center_point = None

        self.sort_outline()
        self.offset_lines()


    @property
    def jack_studs(self):
        return [self.segments[i] for i in self.jack_stud_indices]

    @property
    def sills(self):
        return [self.segments[i] for i in self.sill_indices]

    @property
    def headers(self):
        return [self.segments[i] for i in self.header_indices]

    @property
    def sill_height(self):
        return self.stud_width

    @property
    def header_height(self, segment):
        if not self._header_height:
            self._header_height = math.ceil((segment.length/15)/self.beam_width)*self.beam_width
        return self._header_height

    @property
    def length(self):
        if not self._length:
            _ = self.frame
        return self._length

    @property
    def height(self):
        if not self._height:
            _ = self.frame
        return self._height

    @property
    def frame(self):
        if not self._frame:
            self._frame, self._panel_length, self._panel_height = get_frame(self.points, self.panel_frame.normal, self.zaxis)
        return self._frame

    @property
    def center_point(self):
        if self._center_point:
            pt_xy = Point(self.length/2, self.height/2, 0)
            pt_xy.transform(matrix_from_frame_to_frame(Frame.worldXY(), self.frame))
            self._center_point = pt_xy
        return self._center_point


    def sort_outline(self):
            center = Point(0.0,0.0,0.0)
            for i in range(len(self.outline)-2):
                center += self.outline[i]
            for val in center:
                val /= len(self.outline)-1
            for i, segment in enumerate(self.outline.lines):
                self.segments.append(segment)
                if (
                    angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                    or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):
                    self.jack_stud_indices.append(i)
                else:
                    ray = Line.from_point_and_vector(segment.point_at(0.5), self.z_axis)
                    pts = [intersection_line_segment(ray, seg, 0.01) for seg in self.outline.lines if seg != segment]
                    if len(pts) > 1:
                        print(pts)
                        raise ValueError("Window outline is wonky")
                    else:
                        if dot_vectors(pts[0]-segment.point_at(0.5), self.z_axis) > 0:
                            self.sill_indices.append(i)
                        else:
                            self.header_indices.append(i)


    def offset_lines(self):
        offset_segs = []
        for i, seg in enumerate(self.segments):
            if i in self.header_indices:
                offset_segs.append(Line(offset_line(seg, self.header_height, self.normal)))
            elif i in self.sill_indices:
                offset_segs.append(Line(offset_line(seg, self.sill_height, self.normal)))
            else:
                offset_segs.append(Line(offset_line(seg, self.stud_width, self.normal)))
                self.king_studs.append(offset_line(seg, self.stud_width, self.normal))
            offset_pline_pts = []
            for i in range(len(offset_segs)):
                point = intersection_line_line(offset_segs[i], offset_segs[i - 1], 0.01)[0]
                offset_pline_pts.append(point)
            offset_pline_pts.append(offset_pline_pts[0])
            self.segments = Polyline(offset_pline_pts).lines


    class BeamElement(object):
        def __init__(self, centerline, width, height, z_axis, type=None, segment_index = None, polyline=None):
            self.centerline = centerline
            self.width = width
            self.height = height
            self.z_axis = z_axis
            self.type = type
            self.polyline = polyline
            self.segment_index = segment_index



def get_frame(points, normal, z_axis):
        frame = Frame(points[0], cross_vectors(z_axis, normal), z_axis)
        pts_on_xy = [Point(point.x, point.y, point.z) for point in points]
        for point in pts_on_xy:
            point.transform(matrix_from_frame_to_frame(frame, Frame.worldXY()))
        box_min, _, box_max, _ = bounding_box_xy(pts_on_xy)
        pt = Point(box_min[0], box_min[1], box_min[2])
        box_length = box_max[0] - box_min[0]
        box_height = box_max[1] - box_min[1]
        pt.transform(matrix_from_frame_to_frame(Frame.worldXY(), frame))
        frame.point = pt
        return frame, box_length, box_height
