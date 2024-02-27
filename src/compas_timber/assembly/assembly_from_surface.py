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
from compas_timber.ghpython import CategoryRule
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint



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
        self.sill_height = beam_width
        self.stud_spacing = stud_spacing
        self.z_axis = z_axis or Vector.Zaxis()
        self.sheeting_thickness = sheeting_thickness
        self.sheeting_inside = sheeting_inside
        self.lintel_posts = lintel_posts
        self._normal = None
        self.outer_polyline = None
        self.inner_polylines = []
        self.edges = []
        self._frame = None
        self._panel_length = None
        self._panel_height = None
        self._elements = []
        self.windows = []


        self.parse_loops()
        self.generate_elements()
        self.generate_windows()
        self.generate_studs()


    @property
    def rules(self):
        return [
            CategoryRule(LButtJoint, "edge_stud", "plate"),

            CategoryRule(TButtJoint, "stud", "plate"),
            CategoryRule(TButtJoint, "stud", "header"),
            CategoryRule(TButtJoint, "stud", "sill"),

            CategoryRule(LButtJoint, "jack_stud", "plate"),
            CategoryRule(TButtJoint, "jack_stud", "plate"),
            CategoryRule(LButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "header"),

            CategoryRule(TButtJoint, "king_stud", "plate"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
            CategoryRule(TButtJoint, "king_stud", "header"),

            CategoryRule(TButtJoint, "sill", "jack_stud")

        ]






    @property
    def centerlines(self):
        return [element.centerline for element in self.elements]

    @property
    def beams(self):
        beams = []
        for element in self.elements:
            if element.centerline.length < 0.01:
                print(element.type)
            width = self.header_height if element.type == "header" else self.beam_width
            centerline = element.centerline
            centerline.translate(self.normal * 0.5 * self.beam_height)
            beam = Beam.from_centerline(
                centerline=centerline, width=width, height=self.beam_height, z_vector=self.normal
            )
            beam.attributes["category"] = element.type
            beams.append(beam)
        return beams

    @property
    def points(self):
        return self.outer_polyline.points

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
        return [element for element in self.elements if element.type == "jack_stud"]

    @property
    def king_studs(self):
        return [element for element in self.elements if element.type == "king_stud"]

    @property
    def edge_studs(self):
        return [element for element in self.elements if element.type == "edge_stud"]

    @property
    def studs(self):
        return [element for element in self.elements if element.type == "stud"]

    @property
    def sills(self):
        return [element for element in self.elements if element.type == "sill"]

    @property
    def headers(self):
        return [element for element in self.elements if element.type == "header"]

    @property
    def plates(self):
        return [element for element in self.elements if element.type == "plate"]


    @property
    def elements(self):
        elements = [element for element in self._elements]
        for window in self.windows:
            elements.extend(window.elements)
        return elements

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
                self.outer_polyline = Polyline(polyline_points)
            else:
                self.inner_polylines.append(Polyline(polyline_points))



    def generate_elements(self):
        interior_indices = self.get_interior_segment_indices(self.outer_polyline)
        for i, segment in enumerate(self.outer_polyline.lines):
            element = self.BeamElement(segment, segment_index=i, parent = self)
            if i in interior_indices:
                if (
                angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):
                    element.type = "jack_stud"
                else:
                    element.type = "header"
            else:
                if (
                    angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                    or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):
                    element.type = "edge_stud"
                else:
                    element.type = "plate"
            self._elements.append(element)
        self._elements = self.offset_elements(self._elements)
        for element in self._elements:
            if element.type == "jack_stud":
                king_line = offset_line(element.centerline, self.beam_width, self.normal)
                self._elements.append(self.BeamElement(king_line, type="king_stud", parent=self))

    def get_interior_segment_indices(self, polyline):
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
        if len(out)>0:
            out.insert(1, out[0]-1)
        return out


    def offset_elements(self, element_loop):
        offset_loop = []
        new_elements = []
        for element in element_loop:
            if element.type == "header":
                element.offset(self.header_height/2)
            elif element.type == "sill":
                element.offset(self.sill_height/2)
            elif element.type == "jack_stud":
                element.offset(self.beam_width/2)
            else:
                element.offset(self.beam_width/2)
            offset_loop.append(element)
        for i, element in enumerate(offset_loop):
                point = intersection_line_line(element.centerline, offset_loop[i - 1].centerline, 0.01)[0]
                if point:
                    self.edges.append(Point(*point))

                    element.centerline.start = point
                    offset_loop[i - 1].centerline.end = point
        offset_loop.extend(new_elements)
        return offset_loop

    def generate_windows(self):
        for polyline in self.inner_polylines:
            self.windows.append(self.Window(polyline, self.frame, self.beam_width, self.beam_width, self.header_height, parent=self))


    def generate_studs(self):
        self.generate_studs_lines()
        self.trim_jack_studs()
        self.trim_king_studs()
        self.trim_studs()


    def generate_studs_lines(self):
        x_position = self.stud_spacing
        while x_position < self.panel_length:
            start_point = Point(x_position, 0, 0)
            start_point.transform(matrix_from_frame_to_frame(Frame.worldXY(), self.frame))
            line = Line.from_point_and_vector(start_point, self.z_axis * self.panel_height)
            self._elements.append(self.BeamElement(line, type="stud", parent=self))
            x_position += self.stud_spacing


    def get_element_intersections(self, element, *element_lists_to_intersect):
        intersections = []
        dots = []
        for element_list in element_lists_to_intersect:
            for element_to_intersect in element_list:
                point = intersection_line_segment(element.z_aligned_centerline, element_to_intersect.centerline, 0.01)[0]
                if point:
                    intersections.append(point)
        if len(intersections) > 1:
            intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
            dots = [
                dot_vectors(Vector.from_start_end(element.z_aligned_centerline.start, x), self.z_axis) / element.centerline.length for x in intersections
            ]
        return intersections, dots



    def trim_jack_studs(self):
        for element in self.jack_studs:
            intersections, dots = self.get_element_intersections(element, self.plates, self.headers)
            if len(intersections) > 1:
                bottom = None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                top = element.z_aligned_centerline.end
                if not bottom:
                    bottom = element.z_aligned_centerline.start
            element.set_centerline(Line(bottom, top))


    def trim_king_studs(self):
        for element in self.king_studs:
            intersections, dots = self.get_element_intersections(element, self.plates, self.headers, self.sills)
            if len(intersections) > 1:
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    self.edges.append(intersections[i])
                    if dot < 0.01:
                        bottom = intersections[i]           # last intersection below sill
                    if dot  > 1:
                        top = intersections[i]          # first intersection above header
                        break
                if not bottom:
                    bottom = element.z_aligned_centerline.start
                if not top:
                    top = element.z_aligned_centerline.end
                element.set_centerline(Line(bottom, top))


    def trim_studs(self):
        stud_elements = []
        while len(self.studs) > 0:
            for element in self.elements:
                if element.type == "stud":
                    intersections, _ = self.get_element_intersections(element, self.plates, self.headers, self.sills)
                    while len(intersections) > 1:
                        top = intersections.pop()
                        bottom = intersections.pop()
                        stud_elements.append(self.BeamElement(Line(bottom, top), type="stud", parent=self))
                    self._elements.remove(element)
        self._elements.extend(stud_elements)


    class Window(object):
        def __init__(self, outline, frame, stud_width, sill_height, header_height = None, parent = None):
            self.outline = outline
            self._sill_height = sill_height
            self._header_height = header_height
            self.stud_width = stud_width
            self.panel_frame = frame
            self.parent = parent
            self.z_axis = frame.yaxis
            self.normal = frame.zaxis
            self.jack_stud_indices = []
            self.sill_indices = []
            self.header_indices = []
            self.elements = []
            self._length = None
            self._height = None
            self._normal = None
            self._frame = None
            self._center_point = None

            self.process_outlines()



        @property
        def jack_studs(self):
            return [element for element in self.elements if element.type == "jack_stud"]

        @property
        def sills(self):
            return [element for element in self.elements if element.type == "sill"]

        @property
        def headers(self):
            return [element for element in self.elements if element.type == "header"]

        @property
        def sill_height(self):
            return self.stud_width

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


        def process_outlines(self):
                for i, segment in enumerate(self.outline.lines):

                    element = SurfaceAssembly.BeamElement(segment, segment_index=i, parent=self)
                    if (
                        angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                        or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                    ):
                        element.type = "jack_stud"
                    else:
                        ray = Line.from_point_and_vector(segment.point_at(0.5), self.z_axis)
                        pts = []
                        for seg in self.outline.lines:
                            if seg != segment:
                                pt = intersection_line_segment(ray, seg, 0.01)[0]
                                if pt:
                                    pts.append(Point(*pt))
                        if len(pts) > 1:
                            raise ValueError("Window outline is wonky")
                        elif len(pts) == 1:
                            vector = Vector.from_start_end(ray.start, pts[0])
                            if dot_vectors(vector, self.z_axis) < 0:
                                element.type = "header"
                            else:
                                element.type = "sill"
                    self.elements.append(element)
                self.elements = self.parent.offset_elements(self.elements)
                for element in self.jack_studs:
                    king_line = offset_line(element.centerline, self.stud_width, self.normal)
                    self.elements.append(self.parent.BeamElement(king_line, type="king_stud", parent=self))
                for element in self.elements:
                    self.parent.edges.append(element.centerline)



    class BeamElement(object):
        def __init__(self, centerline, width = None, height = None, z_axis = None, normal = None, type = None, segment_index = None, polyline=None, parent = None):
            self.original_centerline = centerline
            self.centerline = Line(centerline[0], centerline[1])
            self._width = width
            self._height = height
            self._z_axis = z_axis
            self._normal = normal
            self.type = type
            self.polyline = polyline
            self.segment_index = segment_index
            self.parent = parent

        @property
        def width(self):
            return self._width if self._width else self.parent.beam_width

        @property
        def height(self):
            return self._height if self._height else self.parent.beam_height

        @property
        def z_axis(self):
            return self._z_axis if self._z_axis else self.parent.z_axis

        @property
        def z_aligned_centerline(self):
            if dot_vectors(self.centerline.direction, self.parent.z_axis) < 0:
                return Line(self.centerline.end, self.centerline.start)
            else:
                return self.centerline
        @property
        def normal(self):
            return self._normal if self._normal else self.parent.normal

        def offset(self, distance):
            line = offset_line(self.centerline, distance, self.normal)
            self.centerline = Line(line[0], line[1])

        def translate(self, vector):
            self.centerline.transform(vector)

        def to_beam(self):
            centerline = self.centerline.translate(self.normal * 0.5 * self.height)
            return Beam.from_centerline(centerline, self.width, self.height, self.z_axis)

        def set_centerline(self, line):
            self.centerline = line


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
