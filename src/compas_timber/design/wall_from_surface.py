import math

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import bounding_box_xy
from compas.geometry import closest_point_on_plane
from compas.geometry import closest_point_on_segment
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point_sqrd
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_segment
from compas.geometry import matrix_from_frame_to_frame
from compas.geometry import offset_line
from compas.geometry import offset_polyline
from compas.tolerance import Tolerance

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fabrication import FreeContour
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
    jack_studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The jack studs of the assembly.
    king_studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The king studs of the assembly.
    edge_studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The edge studs of the assembly.
    studs : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The studs of the assembly.
    sills : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The sills of the assembly.
    headers : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The headers of the assembly.
    plates : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`

    """

    BEAM_CATEGORY_NAMES = ["stud", "king_stud", "jack_stud", "edge_stud", "plate", "header", "sill"]

    def __init__(
        self,
        surface,
        stud_spacing,
        beam_width=None,
        frame_depth=None,
        z_axis=None,
        tolerance=Tolerance(unit="MM", absolute=1e-3, relative=1e-3),
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
        self._beam_definitions = []
        self._rules = []
        self.windows = []
        self._features = []
        self.beam_dimensions = {}
        self.joint_overrides = joint_overrides
        self.dist_tolerance = tolerance.relative

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
        self.generate_frame()
        self.generate_plates()

    @property
    def z_axis(self):
        cross = cross_vectors(self.normal, self._z_axis)
        return Vector(*cross_vectors(cross, self.normal))

    @property
    def default_rules(self):
        return [
            (CategoryRule(LButtJoint, "edge_stud", "plate") if self.edge_stud_offset == 0 else CategoryRule(TButtJoint, "edge_stud", "plate")),
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
        return [beam_def.centerline for beam_def in self.beam_definitions]

    @property
    def elements(self):
        elements = []
        for window in self.windows:
            self._beam_definitions.extend(window._beam_definitions)
        for beam_def in self._beam_definitions:
            elements.append(beam_def.to_beam())
        elements.extend(self._elements)
        return elements

    @property
    def features(self):
        return self._features

    @property
    def plate_elements(self):
        for plate in self._elements:
            if isinstance(plate, Plate):
                yield plate

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
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "jack_stud"]

    @property
    def king_studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "king_stud"]

    @property
    def edge_studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "edge_stud"]

    @property
    def studs(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "stud"]

    @property
    def sills(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "sill"]

    @property
    def headers(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "header"]

    @property
    def plates(self):
        return [beam_def for beam_def in self._beam_definitions if beam_def.type == "plate"]

    @classmethod
    def beam_category_names(cls):
        return SurfaceModel.BEAM_CATEGORY_NAMES

    def generate_frame(self):
        self.generate_perimeter_beams()
        self.generate_windows()
        self.generate_studs()

    def create_model(self):
        model = TimberModel()
        for element in self.elements:
            model.add_element(element)
        topologies = []
        solver = ConnectionSolver()
        found_pairs = solver.find_intersecting_pairs(list(model.beams), rtree=True, max_distance=self.dist_tolerance)
        for pair in found_pairs:
            beam_a, beam_b = pair
            detected_topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=self.dist_tolerance)
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

    def parse_loops(self):
        for loop in self.surface.loops:
            polyline_points = []
            polyline_length = 0.0
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
                polyline_length += edge.length
            polyline_points.append(polyline_points[0])
            loop_polyline = Polyline(polyline_points)
            offset_dist = self.dist_tolerance * 1000
            if loop.is_outer:
                offset_loop = Polyline(offset_polyline(loop_polyline, offset_dist, self.normal))
                if offset_loop.length > loop_polyline.length:
                    polyline_points.reverse()
                self.outer_polyline = Polyline(polyline_points)
            else:
                offset_loop = Polyline(offset_polyline(loop_polyline, offset_dist, self.normal))
                if offset_loop.length < loop_polyline.length:
                    polyline_points.reverse()
                self.inner_polylines.append(Polyline(polyline_points))

    def generate_perimeter_beams(self):
        interior_indices = self.get_interior_segment_indices(self.outer_polyline)
        for i, segment in enumerate(self.outer_polyline.lines):
            beam_def = self.BeamDefinition(segment, parent=self)
            if i in interior_indices:
                if angle_vectors(segment.direction, self.z_axis, deg=True) < 45 or angle_vectors(segment.direction, self.z_axis, deg=True) > 135:
                    if self.lintel_posts:
                        beam_def.type = "jack_stud"
                    else:
                        beam_def.type = "king_stud"
                else:
                    beam_def.type = "header"
            else:
                if angle_vectors(segment.direction, self.z_axis, deg=True) < 45 or angle_vectors(segment.direction, self.z_axis, deg=True) > 135:
                    beam_def.type = "edge_stud"
                else:
                    beam_def.type = "plate"
            self._beam_definitions.append(beam_def)
        self._beam_definitions = self.offset_elements(self._beam_definitions)
        if self.lintel_posts:
            for beam_def in self._beam_definitions:
                if beam_def.type == "jack_stud":
                    offset = (self.beam_dimensions["jack_stud"][0] + self.beam_dimensions["king_stud"][0]) / 2
                    king_line = offset_line(beam_def.centerline, offset, self.normal)
                    self._beam_definitions.append(self.BeamDefinition(king_line, type="king_stud", parent=self))

    def get_interior_segment_indices(self, polyline):
        points = polyline.points[0:-1]
        out = []
        for index in range(len(points)):
            if index == 0:
                angle = angle_vectors_signed(points[-1] - points[0], points[1] - points[0], self.normal, deg=True)
            elif index == len(points) - 1:
                angle = angle_vectors_signed(points[-2] - points[-1], points[0] - points[-1], self.normal, deg=True)
            else:
                angle = angle_vectors_signed(points[index - 1] - points[index], points[index + 1] - points[index], self.normal, deg=True)
            if angle > 0:
                out.append(index)
        if len(out) > 0:
            out.insert(0, out[0] - 1)
        return set(out)

    def offset_elements(self, element_loop):
        offset_loop = []
        for beam_def in element_loop:
            beam_def.offset(self.beam_dimensions[beam_def.type][0] / 2)
            if beam_def.type == "edge_stud":
                beam_def.offset(self.edge_stud_offset)
            offset_loop.append(beam_def)

        for i, beam_def in enumerate(offset_loop):
            if self.edge_stud_offset > 0:
                if beam_def.type != "plate":
                    element_before = offset_loop[i - 1]
                    element_after = offset_loop[(i + 1) % len(offset_loop)]
                    start_point = intersection_line_line(beam_def.centerline, element_before.centerline, self.dist_tolerance)[0]
                    end_point = intersection_line_line(beam_def.centerline, element_after.centerline, self.dist_tolerance)[0]
                    if start_point and end_point:
                        beam_def.centerline = Line(start_point, end_point)
                    else:
                        raise ValueError("edges are parallel, no intersection found")
            else:
                element_before = offset_loop[i - 1]
                element_after = offset_loop[(i + 1) % len(offset_loop)]
                start_point, _ = intersection_line_line(beam_def.centerline, element_before.centerline, self.dist_tolerance)
                end_point, _ = intersection_line_line(beam_def.centerline, element_after.centerline, self.dist_tolerance)
                if start_point and end_point:
                    beam_def.centerline = Line(start_point, end_point)
        return offset_loop

    def generate_windows(self):
        for polyline in self.inner_polylines:
            self.windows.append(self.Window(polyline, parent=self))
            self._beam_definitions.extend(self.windows[-1]._beam_definitions)

    def generate_studs(self):
        self.generate_stud_lines()
        self.trim_jack_studs()
        self.trim_king_studs()
        self.trim_studs()
        self.cull_overlaps()

    def generate_stud_lines(self):
        x_position = self.stud_spacing
        while x_position < self.panel_length - self.beam_width:
            start_point = Point(x_position, 0, 0)
            start_point.transform(matrix_from_frame_to_frame(Frame.worldXY(), self.frame))
            line = Line.from_point_and_vector(start_point, self.z_axis * self.panel_height)
            self._beam_definitions.append(self.BeamDefinition(line, type="stud", parent=self))
            x_position += self.stud_spacing

    def get_beam_intersections(self, beam_def, *element_lists_to_intersect):
        intersections = []
        dots = []
        for element_list in element_lists_to_intersect:
            for element_to_intersect in element_list:
                point = intersection_line_segment(beam_def.z_aligned_centerline, element_to_intersect.centerline, 0.01)[0]
                if point:
                    intersections.append(point)
        if len(intersections) > 1:
            intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
            dots = [dot_vectors(Vector.from_start_end(beam_def.z_aligned_centerline.start, x), self.z_axis) / beam_def.centerline.length for x in intersections]
        return intersections, dots

    def trim_jack_studs(self):
        for beam_def in self.jack_studs:
            intersections, dots = self.get_beam_intersections(beam_def, self.plates, self.headers)
            if len(intersections) > 1:
                bottom = None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                top = beam_def.z_aligned_centerline.end
                if not bottom:
                    bottom = beam_def.z_aligned_centerline.start
            beam_def.set_centerline(Line(bottom, top))

    def trim_king_studs(self):
        for beam_def in self.king_studs:
            intersections, dots = self.get_beam_intersections(beam_def, self.plates, self.headers, self.sills)
            if len(intersections) > 1:
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    if dot < -0.01:
                        bottom = intersections[i]  # last intersection below sill
                    if dot > 1.01:
                        top = intersections[i]  # first intersection above header
                        break
                if not bottom:
                    bottom = beam_def.z_aligned_centerline.start
                if not top:
                    top = beam_def.z_aligned_centerline.end
                beam_def.set_centerline(Line(bottom, top))

    def trim_studs(self):
        stud_elements = []
        while len(self.studs) > 0:
            for beam_def in self._beam_definitions:
                if beam_def.type == "stud":
                    intersections, _ = self.get_beam_intersections(beam_def, self.plates, self.headers, self.sills)
                    while len(intersections) > 1:
                        top = intersections.pop()
                        bottom = intersections.pop()
                        stud_elements.append(self.BeamDefinition(Line(bottom, top), type="stud", parent=self))
                    self._beam_definitions.remove(beam_def)
        self._beam_definitions.extend(stud_elements)

    def cull_overlaps(self):
        for beam_def in self.studs:
            for other_element in self.king_studs + self.jack_studs + self.edge_studs:
                if self.distance_between_elements(beam_def, other_element) < (self.beam_dimensions[beam_def.type][0] + self.beam_dimensions[other_element.type][0]) / 2:
                    self._beam_definitions.remove(beam_def)
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

    def generate_plates(self):
        if self.sheeting_inside:
            self._elements.append(Plate(self.outer_polyline, self.sheeting_inside))
        if self.sheeting_outside:
            pline = self.outer_polyline.copy()
            pline.translate(self.frame.zaxis * (self.frame_depth + self.sheeting_outside))
            self._elements.append(Plate(pline, self.sheeting_outside))
        for window in self.windows:
            for plate in self.plate_elements:
                window.apply_contour_to_plate(plate)

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
        beam_definions : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
            The beam_definions of the window.
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
            self._beam_definitions = []
            self._length = None
            self._height = None
            self._frame = None
            self.dist_tolerance = parent.dist_tolerance
            self.process_outlines()

        @property
        def jack_studs(self):
            return [beam_def for beam_def in self._beam_definitions if beam_def.type == "jack_stud"]

        @property
        def sills(self):
            return [beam_def for beam_def in self._beam_definitions if beam_def.type == "sill"]

        @property
        def headers(self):
            return [beam_def for beam_def in self._beam_definitions if beam_def.type == "header"]

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
                self._frame, self._panel_length, self._panel_height = get_frame(self.points, self.parent.normal, self.zaxis)
            return self._frame

        def apply_contour_to_plate(self, plate):
            projected_points = []
            for point in self.outline.points:
                projected_points.append(closest_point_on_plane(point, Plane.from_frame(plate.frame)))
            feature = FreeContour.from_polyline_and_element(Polyline(projected_points), plate)
            plate.add_feature(feature)

        def process_outlines(self):
            for i, segment in enumerate(self.outline.lines):
                beam_def = SurfaceModel.BeamDefinition(segment, parent=self)
                if angle_vectors(segment.direction, self.z_axis, deg=True) < 1 or angle_vectors(segment.direction, self.z_axis, deg=True) > 179:
                    if self.parent.lintel_posts:
                        beam_def.type = "jack_stud"
                    else:
                        beam_def.type = "king_stud"
                else:
                    ray = Line.from_point_and_vector(segment.point_at(0.5), self.z_axis)
                    pts = []
                    for seg in self.outline.lines:
                        if seg != segment:
                            pt = intersection_line_segment(ray, seg, self.dist_tolerance)[0]
                            if pt:
                                pts.append(Point(*pt))
                    if len(pts) > 1:
                        raise ValueError("Window outline is wonky")
                    elif len(pts) == 1:
                        vector = Vector.from_start_end(ray.start, pts[0])
                        if dot_vectors(vector, self.z_axis) < 0:
                            beam_def.type = "header"
                        else:
                            beam_def.type = "sill"
                self._beam_definitions.append(beam_def)
            self._beam_definitions = self.parent.offset_elements(self._beam_definitions)
            if self.parent.lintel_posts:
                for beam_def in self.jack_studs:
                    offset = (self.parent.beam_dimensions["jack_stud"][0] + self.parent.beam_dimensions["king_stud"][0]) / 2
                    king_line = offset_line(beam_def.centerline, offset, self.normal)
                    self._beam_definitions.append(self.parent.BeamDefinition(king_line, type="king_stud", parent=self))

    class BeamDefinition(object):
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
