import math

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import bounding_box_xy
from compas.geometry import closest_point_on_segment
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point_sqrd
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import matrix_from_frame_to_frame
from compas.geometry import offset_line
from compas.geometry import offset_polyline

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


class SurfaceModel(object):
    """Create a timber assembly from a surface.

    Parameters
    ----------
    surface : :class:`compas.geometry.Surface`
        The surface to create the assembly from. must be planar.
    beam_width : float
        The height of the beams aka thickness of wall cavity normal to the surface.
    frame_depth : float
        The width of the beams.
    stud_spacing : float
        The spacing between the studs.
    z_axis : :class:`compas.geometry.Vector`, optional
        Determines the orientation of the posts inside the frame.
        Default is ``Vector.Zaxis``.


    Attributes
    ----------
    beams : list of :class:`compas_timber.elements.Beam`
        The beams of the assembly.
    rules : list of :class:`compas_timber.design.CategoryRule`
        The rules for the assembly.
    centerlines : list of :class:`compas.geometry.Line`
        The centerlines of the beams.
    normal : :class:`compas.geometry.Vector`
        The normal of the surface.
    panel_length : float
        The length of the panel.
    panel_height : float
        The height of the panel.
    frame : :class:`compas.geometry.Frame`
        The frame of the assembly.
    jack_studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
        The jack studs of the assembly.
    king_studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
        The king studs of the assembly.
    edge_studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
        The edge studs of the assembly.
    studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
        The studs of the assembly.
    sills : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
        The sills of the assembly.
    headers : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
        The headers of the assembly.
    plates : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`

    """

    BEAM_CATEGORY_NAMES = ["stud", "king_stud", "jack_stud", "edge_stud", "plate", "header", "sill"]

    def __init__(
        self,
        surface,
        stud_spacing,
        beam_width=None,
        frame_depth=None,
        z_axis=None,
        sheeting_outside=None,
        sheeting_inside=None,
        lintel_posts=True,
        edge_stud_offset=0.0,
        custom_dimensions=None,
        joint_overrides=None,
    ):
        self.surface = surface
        self.beam_width = beam_width
        self.frame_depth = frame_depth
        self.stud_spacing = stud_spacing
        self._z_axis = z_axis or Vector.Zaxis()
        self.sheeting_outside = sheeting_outside
        self.sheeting_inside = sheeting_inside
        self.edge_stud_offset = edge_stud_offset or 0.0
        self.lintel_posts = lintel_posts
        self._normal = None
        self.outer_polyline = None
        self.inner_polylines = []
        self.edges = []
        self._frame = None
        self._panel_length = None
        self._panel_height = None
        self._elements = []
        self._rules = []
        self.windows = []
        self.beam_dimensions = {}
        self.joint_overrides = joint_overrides

        for key in self.BEAM_CATEGORY_NAMES:
            self.beam_dimensions[key] = [self.beam_width, self.frame_depth]
        if custom_dimensions:
            for key, value in custom_dimensions.items():
                if value:
                    if value[0] != 0:
                        self.beam_dimensions[key][0] = value[0]
                    if value[1] != 0:
                        self.beam_dimensions[key][1] = value[1]
        self.parse_loops()
        self.generate_perimeter_elements()
        self.generate_windows()
        self.generate_studs()

    @property
    def z_axis(self):
        cross = cross_vectors(self.normal, self._z_axis)
        return Vector(*cross_vectors(cross, self.normal))

    @property
    def default_rules(self):
        return [
            (
                CategoryRule(LButtJoint, "edge_stud", "plate")
                if self.edge_stud_offset == 0
                else CategoryRule(TButtJoint, "edge_stud", "plate")
            ),
            CategoryRule(TButtJoint, "stud", "plate"),
            CategoryRule(TButtJoint, "stud", "header"),
            CategoryRule(TButtJoint, "stud", "sill"),
            CategoryRule(LButtJoint, "jack_stud", "plate"),
            CategoryRule(TButtJoint, "jack_stud", "plate"),
            CategoryRule(LButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "jack_stud", "header"),
            CategoryRule(TButtJoint, "king_stud", "plate"),
            CategoryRule(LButtJoint, "king_stud", "plate"),
            CategoryRule(TButtJoint, "king_stud", "sill"),
            CategoryRule(TButtJoint, "king_stud", "header"),
            CategoryRule(TButtJoint, "sill", "jack_stud"),
        ]

    @property
    def rules(self):
        if not self._rules:
            self._rules = self.default_rules
            if self.joint_overrides:
                for rule in self.joint_overrides:
                    rule_set = set([rule.category_a, rule.category_b])
                    for i, _rule in enumerate(self._rules):
                        _set = set([_rule.category_a, _rule.category_b])
                        if rule_set == _set:
                            self._rules[i] = rule
                            break
        return self._rules

    @property
    def centerlines(self):
        return [element.centerline for element in self.elements]

    def create_model(self):
        model = TimberModel()
        for beam in self.beams:
            model.add_beam(beam)
        topologies = []
        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(model.beams, rtree=True, max_distance=0.1)
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=0.1)
            if not detected_topo == JointTopology.TOPO_UNKNOWN:
                topologies.append({"detected_topo": detected_topo, "beam_a": beam_a, "beam_b": beam_b})
                for rule in self.rules:
                    if not rule.comply(pair):
                        continue
                    if rule.joint_type.SUPPORTED_TOPOLOGY != detected_topo:
                        continue
                    else:
                        if rule.joint_type == LButtJoint:
                            beam_a, beam_b = rule.reorder([beam_a, beam_b])
                        rule.joint_type.create(model, beam_a, beam_b, **rule.kwargs)
        model.set_topologies(topologies)
        return model

    @property
    def beams(self):
        beams = []
        for element in self.elements:
            beams.append(element.to_beam())
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

    @classmethod
    def beam_category_names(cls):
        return SurfaceModel.BEAM_CATEGORY_NAMES

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
                offset_loop = Polyline(offset_polyline(Polyline(polyline_points), 10, self.normal))
                if offset_loop.length > Polyline(polyline_points).length:
                    polyline_points.reverse()
                self.outer_polyline = Polyline(polyline_points)
            else:
                offset_loop = Polyline(offset_polyline(Polyline(polyline_points), 10, self.normal))
                if offset_loop.length < Polyline(polyline_points).length:
                    polyline_points.reverse()
                self.inner_polylines.append(Polyline(polyline_points))

    def generate_perimeter_elements(self):
        interior_indices = self.get_interior_segment_indices(self.outer_polyline)
        for i, segment in enumerate(self.outer_polyline.lines):
            element = self.BeamElement(segment, parent=self)
            if i in interior_indices:
                if (
                    angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                    or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):

                    if self.lintel_posts:
                        element.type = "jack_stud"
                    else:
                        element.type = "king_stud"
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
        if self.lintel_posts:
            for element in self._elements:
                if element.type == "jack_stud":
                    offset = (self.beam_dimensions["jack_stud"][0] + self.beam_dimensions["king_stud"][0]) / 2
                    king_line = offset_line(element.centerline, offset, self.normal)
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
        if len(out) > 0:
            out.insert(1, out[0] - 1)
        return out

    def offset_elements(self, element_loop):
        offset_loop = []
        for element in element_loop:
            element.offset(self.beam_dimensions[element.type][0] / 2)
            if element.type == "edge_stud":
                element.offset(self.edge_stud_offset)
            offset_loop.append(element)
            # self.edges.append(Line(element.centerline[0], element.centerline[1]))
        for i, element in enumerate(offset_loop):
            if self.edge_stud_offset > 0:
                if element.type != "plate":
                    element_before = offset_loop[i - 1]
                    element_after = offset_loop[(i + 1) % len(offset_loop)]
                    start_point = intersection_line_line(element.centerline, element_before.centerline, 0.01)[0]
                    end_point = intersection_line_line(element.centerline, element_after.centerline, 0.01)[0]
                    if start_point and end_point:
                        element.centerline = Line(start_point, end_point)
            else:
                element_before = offset_loop[i - 1]
                element_after = offset_loop[(i + 1) % len(offset_loop)]
                start_point = intersection_line_line(element.centerline, element_before.centerline, 0.01)[0]
                end_point = intersection_line_line(element.centerline, element_after.centerline, 0.01)[0]
                if start_point and end_point:
                    element.centerline = Line(start_point, end_point)
        return offset_loop

    def generate_windows(self):
        for polyline in self.inner_polylines:
            self.windows.append(self.Window(polyline, parent=self))

    def generate_studs(self):
        self.generate_stud_lines()
        self.trim_jack_studs()
        self.trim_king_studs()
        self.trim_studs()
        self.cull_overlaps()

    def generate_stud_lines(self):
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
                point = intersection_line_segment(element.z_aligned_centerline, element_to_intersect.centerline, 0.01)[
                    0
                ]
                if point:
                    intersections.append(point)
        if len(intersections) > 1:
            intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
            dots = [
                dot_vectors(Vector.from_start_end(element.z_aligned_centerline.start, x), self.z_axis)
                / element.centerline.length
                for x in intersections
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
                    if dot < -0.01:
                        bottom = intersections[i]  # last intersection below sill
                    if dot > 1.01:
                        top = intersections[i]  # first intersection above header
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

    def cull_overlaps(self):
        for element in self.studs:
            for other_element in self.king_studs + self.jack_studs:
                if (
                    self.distance_between_elements(element, other_element)
                    < (self.beam_dimensions[element.type][0] + self.beam_dimensions[other_element.type][0]) / 2
                ):
                    self._elements.remove(element)
                    break

    def distance_between_elements(self, element_one, element_two):
        distances = []
        for pt in element_one.centerline:
            cp = closest_point_on_segment(pt, element_two.centerline)
            distances.append(distance_point_point_sqrd(pt, cp))
        for pt in element_two.centerline:
            cp = closest_point_on_segment(pt, element_one.centerline)
            distances.append(distance_point_point_sqrd(pt, cp))
        return math.sqrt(min(distances))

    class Window(object):
        """
        A window object for the SurfaceAssembly.

        Parameters
        ----------
        outline : :class:`compas.geometry.Polyline`
            The outline of the window.
        sill_height : float, optional
            The height of the sill.
        header_height : float, optional
            The height of the header.
        parent : :class:`compas_timber.model.SurfaceAssembly`
            The parent of the window.

        Attributes
        ----------
        outline : :class:`compas.geometry.Polyline`
            The outline of the window.
        sill_height : float
            The height of the sill.
        header_height : float
            The height of the header.
        parent : :class:`compas_timber.model.SurfaceAssembly`
            The parent of the window.
        z_axis : :class:`compas.geometry.Vector`
            The z axis of the parent.
        normal : :class:`compas.geometry.Vector`
            The normal of the parent.
        beam_dimensions : dict
            The beam dimensions of the parent.
        elements : list of :class:`compas_timber.model.SurfaceAssembly.BeamElement`
            The elements of the window.
        length : float
            The length of the window.
        height : float
            The height of the window.
        frame : :class:`compas.geometry.Frame`
            The frame of the window.

        """

        def __init__(self, outline, sill_height=None, header_height=None, parent=None):
            self.outline = outline
            if sill_height:
                self.sill_height = sill_height
            else:
                self.sill_height = parent.beam_dimensions["sill"][0]
            if header_height:
                self.header_height = header_height
            else:
                self.header_height = parent.beam_dimensions["header"][0]
            self.parent = parent
            self.z_axis = parent.frame.yaxis
            self.normal = parent.frame.zaxis
            self.beam_dimensions = parent.beam_dimensions
            self.elements = []
            self._length = None
            self._height = None
            self._frame = None
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
                self._frame, self._panel_length, self._panel_height = get_frame(
                    self.points, self.parent.normal, self.zaxis
                )
            return self._frame

        def process_outlines(self):
            for i, segment in enumerate(self.outline.lines):
                element = SurfaceModel.BeamElement(segment, parent=self)
                if (
                    angle_vectors(segment.direction, self.z_axis, deg=True) < 1
                    or angle_vectors(segment.direction, self.z_axis, deg=True) > 179
                ):
                    if self.parent.lintel_posts:
                        element.type = "jack_stud"
                    else:
                        element.type = "king_stud"
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
            if self.parent.lintel_posts:
                for element in self.jack_studs:
                    offset = (
                        self.parent.beam_dimensions["jack_stud"][0] + self.parent.beam_dimensions["king_stud"][0]
                    ) / 2
                    king_line = offset_line(element.centerline, offset, self.normal)
                    self.elements.append(self.parent.BeamElement(king_line, type="king_stud", parent=self))

    class BeamElement(object):
        """
        Container for Beam attributes before beam is instantiated.

        Parameters
        ----------
        centerline : :class:`compas.geometry.Line`
            The centerline of the beam.
        width : float, optional
            The width of the beam.
        height : float, optional
            The height of the beam.
        z_axis : :class:`compas.geometry.Vector`, optional
            The z axis of the beam.
        normal : :class:`compas.geometry.Vector`, optional
            The normal of the beam.
        type : str, optional
            The type of the beam.
        polyline : :class:`compas.geometry.Polyline`, optional
            The polyline of the beam.
        parent : :class:`compas_timber.model.SurfaceAssembly` or :class:`compas_timber.model.SurfaceAssembly.Window`
            The parent of the beam.

        Attributes
        ----------
        centerline : :class:`compas.geometry.Line`
            The centerline of the beam element.
        width : float
            The width of the beam element.
        height : float
            The height of the beam element.
        z_axis : :class:`compas.geometry.Vector`
            The z axis of the parent (Not the Beam).
        normal : :class:`compas.geometry.Vector`
            The normal of the parent.


        """

        def __init__(
            self,
            centerline,
            width=None,
            height=None,
            z_axis=None,
            normal=None,
            type=None,
            parent=None,
        ):
            self.original_centerline = centerline
            self.centerline = Line(centerline[0], centerline[1])
            self._width = width
            self._height = height
            self._normal = normal
            self.type = type
            self.parent = parent

        @property
        def width(self):
            return self._width if self._width else self.parent.beam_dimensions[self.type][0]

        @property
        def height(self):
            return self._height if self._height else self.parent.beam_dimensions[self.type][1]

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
            centerline = Line(*self.centerline)
            centerline.translate(self.normal * 0.5 * self.height)
            beam = Beam.from_centerline(centerline, self.width, self.height, self.normal)
            beam.attributes["category"] = self.type
            return beam

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
