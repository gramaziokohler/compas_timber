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
    def __init__(self, surface, beam_width, beam_height, stud_spacing, z_axis = Vector.Zaxis(), sheeting_thickness = None, sheeting_inside = None, lintel_posts = True):
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
        self.stud_spacing = stud_spacing
        self.z_axis = z_axis
        self.sheeting_thickness = sheeting_thickness
        self.sheeting_inside = sheeting_inside
        self.lintel_posts = lintel_posts
        self.frame = None
        self._normal = None
        self.outer_polyline = None
        self.inner_polylines = []
        self.points = []
        self.test_points = []
        self.edges = []
        self.panel_length = 0
        self.panel_height = 0


        self.parse_loops()
        self.generate_frame()
        self.parse_outline()
        self.generate_studs()
        self.generate_openings()

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
                beam = Beam.from_centerline(centerline=line, width=self.beam_width, height=self.beam_height, z_vector=self.normal)
                beam.attributes["category"] = str(key)
                print(beam.attributes["category"])
                beams.append(beam)
        return beams


    @property
    def normal(self):
        if not self._normal:
            self._normal = self.surface.native_brep.Faces[0].NormalAt(0.5, 0.5)
        return self._normal


    def generate_frame(self):
        frame = Frame(self.points[0], cross_vectors(self.z_axis, self.normal), self.z_axis)
        pts_on_xy = [Point(point.x, point.y, point.z) for point in self.points]
        for point in pts_on_xy:
            point.transform(matrix_from_frame_to_frame(frame, Frame.worldXY()))
        box_min, _, box_max, _ = bounding_box_xy(pts_on_xy)
        pt = Point(box_min[0], box_min[1], box_min[2])
        self.panel_length = box_max[0] - box_min[0]
        self.panel_height = box_max[1] - box_min[1]
        pt.transform(matrix_from_frame_to_frame(Frame.worldXY(), frame))
        frame.point = pt
        self.frame = frame





    def parse_loops(self):
        for loop in self.surface.loops:
            polyline_points = []
            for i, edge in enumerate(loop.edges):
                self.edges.append(Line(edge.start_vertex.point, edge.end_vertex.point))
                if not edge.is_line:
                    raise ValueError('function only supprorts polyline edges')
                if edge.start_vertex.point in [loop.edges[i-1].start_vertex.point, loop.edges[i-1].end_vertex.point]:
                    polyline_points.append(edge.start_vertex.point)
                else:
                    polyline_points.append(edge.end_vertex.point)
            polyline_points.append(polyline_points[0])

            if loop.is_outer:
                self.points = polyline_points
                polyline = Polyline(polyline_points)
                polyline.translate(self.normal * 0.5 * self.beam_height)
                polyline = self.offset_closed_pline(polyline, self.beam_width/2, self.normal)
                self.outer_polyline = polyline
            else:
                polyline = Polyline(polyline_points)
                polyline.translate(self.normal * 0.5 * self.beam_height)
                polyline = self.offset_closed_pline(polyline, self.beam_width/2, self.normal)
                self.inner_polylines.append(polyline)


    def get_interior_corner(self, polyline):
        out = []
        for index in range(len(polyline)):
            if index == 0:
                angle = angle_vectors_signed(polyline[-1] - polyline[0], polyline[1] - polyline[0], self.normal, deg = True)
            elif index == len(polyline) - 1:
                angle = angle_vectors_signed(polyline[-2] - polyline[-1], polyline[0] - polyline[-1], self.normal, deg = True)
            else:
                angle = angle_vectors_signed(polyline[index-1] - polyline[index], polyline[index+1] - polyline[index], self.normal, deg = True)
            if angle > 0:
                out.append(index)
        return out


    def sort_interior_and_exterior_segments(self, polyline):
        interior = []
        exterior = []
        interior_corners = self.get_interior_corner(polyline)
        for segment in polyline.lines:
            is_interior = False
            for i in interior_corners:
                if polyline[i] == segment[0] or polyline[i] == segment[1]:
                    interior.append(segment)
                    is_interior = True
                    break
            if not is_interior:
                exterior.append(segment)
        return interior, exterior


    def parse_outline(self):

        beams = []
        joints = []
        sheeting = []

        self.edge_studs = []
        self.cripples = []
        self.king_studs = []
        self.headers = []
        self.sills = []
        self.headers = []
        self.plates = []
        self.jack_studs = []

        interior_segments, exterior_segments = self.sort_interior_and_exterior_segments(self.outer_polyline)
        # self.edges = interior_segments
        for segment in interior_segments:
            if angle_vectors(segment.direction, self.z_axis, deg = True) < 1 or angle_vectors(segment.direction, self.z_axis, deg = True) > 179:
                self.jack_studs.append(segment)
                pts = offset_line(segment, self.beam_width, self.normal)
                self.king_studs.append(Line(pts[0], pts[1]))
            else:
                self.headers.append(segment)

        for segment in exterior_segments:
            if angle_vectors(segment.direction, self.z_axis, deg = True) < 1 or angle_vectors(segment.direction, self.z_axis, deg = True) > 179:
                self.edge_studs.append(segment)
            else:
                self.plates.append(segment)

    def offset_closed_pline(self, polyline, distance, normal):
            offset_segs = []
            offset_pline_pts = []
            for segment in polyline.lines:
                offset_segs.append(Polyline(offset_line(segment, distance, normal)))
            for i in range(len(offset_segs)):
                point = intersection_line_line(offset_segs[i], offset_segs[i-1], 0.01)[0]
                offset_pline_pts.append(point)
            offset_pline_pts.append(offset_pline_pts[0])
            return Polyline(offset_pline_pts)

    def generate_studs(self):
        x_position = self.stud_spacing + (self.beam_width/2.0)
        studs = []
        while x_position < self.panel_length:
            start_point = Point(x_position, 0,0)
            start_point.transform(matrix_from_frame_to_frame(Frame.worldXY(), self.frame))
            start_point.translate(self.normal * 0.5 * self.beam_height)
            studs.append(Line.from_point_and_vector(start_point, self.z_axis*self.panel_height))
            x_position += self.stud_spacing
        self.studs=studs

    def generate_openings(self):
        for outline in self.inner_polylines:
            horos = []
            for segment in outline.lines:
                if angle_vectors(segment.direction, self.z_axis, deg = True) < 1 or angle_vectors(segment.direction, self.z_axis, deg = True) > 179:
                    self.jack_studs.append(segment)
                    pts = offset_line(segment, self.beam_width, self.normal)
                    self.king_studs.append(Line(pts[0], pts[1]))
                else:
                    horos.append(segment)

            horos.sort(key=lambda x: dot_vectors(x.start+x.end, self.z_axis ))
            self.sills.append(horos[0])
            self.headers.append(horos[-1])



        new_lines = []
        for line in self.jack_studs:

            intersections = []
            line_pts = [line.start, line.end]
            line_pts.sort(key=lambda x: dot_vectors(x, self.z_axis))
            for plate in self.plates:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            for plate in self.headers:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            if len(intersections)>1:
                intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
                dots = [dot_vectors(Vector.from_start_end(line_pts[0], x) , self.z_axis)/line.length for x in intersections]
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                    if abs(dot-1) < 0.01:
                        top = intersections[i]
                        break
                if not bottom:
                    bottom = line_pts[0]
                if not top:
                    top = line_pts[1]
            new_lines.append(Line(bottom, top))

        self.jack_studs = new_lines

        new_lines = []
        for line in self.king_studs:
            intersections = []
            line_pts = [line.start, line.end]
            line_pts.sort(key=lambda x: dot_vectors(x, self.z_axis))
            for plate in self.plates:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            for plate in self.headers:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            for plate in self.sills:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            if len(intersections)>1:
                intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
                dots = [dot_vectors(Vector.from_start_end(line_pts[0], x), self.z_axis)/line.length for x in intersections]
                bottom, top = None, None
                for i, dot in enumerate(dots):
                    if dot < 0:
                        bottom = intersections[i]
                    if dot > 1:
                        top = intersections[i]
                        break
                if not bottom:
                    bottom = line_pts[0]
                if not top:
                    top = line_pts[1]
            new_lines.append(Line(bottom, top))

        self.king_studs = new_lines
        new_lines = []
        for line in self.studs:
            intersections = []
            line_pts = [line.start, line.end]
            line_pts.sort(key=lambda x: dot_vectors(x, self.z_axis))
            for plate in self.plates:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            for plate in self.headers:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            for plate in self.sills:
                point = intersection_line_segment(line, plate, 0.01)[0]
                if point:
                    intersections.append(point)
            if len(intersections)>1:
                intersections.sort(key=lambda x: dot_vectors(x, self.z_axis))
            while len(intersections) > 1:
                top = intersections.pop()
                bottom = intersections.pop()
                new_lines.append(Line(bottom, top))

        self.studs = new_lines
