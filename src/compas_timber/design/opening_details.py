from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import distance_point_line
from compas.geometry import dot_vectors
from compas.geometry import intersection_segment_segment

from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.design import CategoryRule
from compas_timber.design.details import DetailBase
from compas_timber.fabrication.free_contour import FreeContour
from compas_timber.utils import do_segments_overlap
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import get_segment_overlap
from compas_timber.utils import is_point_in_polyline
from compas_timber.utils import move_polyline_segment_to_plane
from compas_timber.utils import split_beam_at_lengths
from compas_timber.utils import intersection_line_beams


class OpeningPopulator(object):
    """Class to populate openings in a slab."""

    def __init__(self, opening, slab, detail_set):
        self.opening = opening
        self.slab = slab
        self.detail_set = detail_set
        self.oriented_outline = self._get_oriented_outline()

    def populate_openings(self):
        """Populate openings in the slab."""
        for opening in self.slab.openings:
            self._populate_opening(opening)

    def _get_oriented_outline(self):
        outline = self.opening.outline.copy()
        outline.transform(self.slab.transformation.inverse())
        outline.transform(self.slab_populator.transformation.inverse())
        return outline


class OpeningDetailBase(DetailBase):
    """Base class for opening detail sets.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    BEAM_CATEGORY_NAMES = ["header", "sill", "king_stud", "jack_stud"]


    def _create_frame_polyline(self, opening, slab_populator):
        """Bounding rectangle aligned orthogonal to the slab_populator.stud_direction."""
        frame = Frame(opening.outline[0], cross_vectors(slab_populator.stud_direction, slab_populator.normal), slab_populator.stud_direction)
        rebase = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        box = Box.from_points(opening.outline.transformed(rebase))
        rebase.invert()
        box.transform(rebase)
        opening.frame_polyline = Polyline([box.corner(0), box.corner(1), box.corner(2), box.corner(3), box.corner(0)])
        opening.frame_polyline.translate(slab_populator.normal * slab_populator.detail_set.sheeting_inside)
        return opening.frame_polyline

    def _add_jack_studs(self, opening, slab_populator):
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        opening.beams.append(self.beam_from_category(opening.king_studs[0].centerline, "jack_stud", slab_populator, normal_offset=False, opening_edge_index=2))
        opening.beams.append(self.beam_from_category(opening.king_studs[1].centerline, "jack_stud", slab_populator, normal_offset=False, opening_edge_index=0))
        opening.king_studs[0].frame.translate(
            get_polyline_segment_perpendicular_vector(opening.frame_polyline, 2) * (beam_dimensions["jack_stud"][0] + beam_dimensions["king_stud"][0]) * 0.5
        )
        opening.king_studs[1].frame.translate(
            get_polyline_segment_perpendicular_vector(opening.frame_polyline, 0) * (beam_dimensions["jack_stud"][0] + beam_dimensions["king_stud"][0]) * 0.5
        )

    def _join_king_studs(self, opening, slab_populator):
        """Extend king studs and join them to neighboring slab populator beams."""
        joints = []
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        for king_stud in opening.king_studs:
            intersections = []
            # get beams to intersect with
            beams = []
            for val in slab_populator.edge_beams.values():
                beams.extend(val)
            for op in slab_populator.openings:
                if op != opening:
                    beams.extend([op.sill, op.header])
            # get intersections
            intersections = intersection_line_beams(king_stud.centerline, beams, max_distance=beam_dimensions["king_stud"][0])
            if not intersections:
                continue
            # get closest intersections above and below the king stud
            intersections.sort(key=lambda x: x["dot"])
            bottom_int = None
            top_int = None
            for intersection in intersections:
                if intersection["dot"] < 0:
                    bottom_int = intersection
                else:
                    top_int = intersection
                    break
            # create joints
            joints.append(self.get_joint_from_elements(king_stud, bottom_int["beam"], self.rules))
            joints.append(self.get_joint_from_elements(king_stud, top_int["beam"], self.rules))
        return joints

    def _join_jack_studs(self, opening, slab_populator):
        joints = []
        beam_dimensions = self.get_beam_dimensions(slab_populator)
        for jack_stud in opening.jack_studs:
            intersections = []
            # get beams to intersect with
            beams = []
            for val in slab_populator.edge_beams.values():
                beams.extend(val)
            for op in slab_populator.openings:
                if op != opening:
                    beams.extend([op.header])
            # get intersections
            intersections = intersection_line_beams(jack_stud.centerline, beams, max_distance=beam_dimensions["jack_stud"][0])
            if not intersections:
                continue
            # get closest intersection to the bottom of the jack stud
            intersections.sort(key=lambda x: x["dot"])
            bottom_int = None
            for intersection in intersections:
                if intersection["dot"] < 0:
                    bottom_int = intersection
                else:
                    break
            # create joint
            joints.append(self.get_joint_from_elements(jack_stud, bottom_int["beam"], self.rules))
        return joints

    def cull_and_split_studs(self, opening, slab_populator):
        """Split the bottom plate beam for door openings."""
        int_beams = [opening.sill, opening.header] if opening.sill else [opening.header]
        new_studs = []
        to_split, to_cull = self._parse_studs(opening, slab_populator)
        for stud in to_split + to_cull:
            slab_populator.elements.remove(stud)
        while to_split:
            stud = to_split.pop(0)
            dots = []
            for int_beam in int_beams:
                intersection = intersection_segment_segment(stud.centerline, int_beam.centerline)[0]
                if not intersection:
                    continue
                dots.append(dot_vectors(stud.centerline.direction, Vector.from_start_end(stud.centerline.start, intersection)))
            stud_segs = split_beam_at_lengths(stud, dots)
            opening.joint_tuples.extend([(pair) for pair in zip(stud_segs, int_beams)])
            for seg in stud_segs:
                if not is_point_in_polyline(seg.midpoint, opening.frame_polyline, in_plane=False):
                    new_studs.append(seg)
        slab_populator.elements.extend(new_studs)


    def _parse_studs(self, opening, slab_populator):
        """Cull and split the studs for the opening."""
        cull_outer_edge = [dot_vectors(slab_populator._slab.frame.xaxis, Vector.from_start_end(slab_populator._slab.frame.point, king.midpoint)) for king in opening.king_studs]
        cull_outer_edge.sort()
        if opening.jack_studs:
            cull_inner_edge = [
                dot_vectors(slab_populator._slab.frame.xaxis, Vector.from_start_end(slab_populator._slab.frame.point, jack.midpoint)) for jack in opening.jack_studs
            ]
            cull_inner_edge.sort()
            cull_inner_edge[0] += opening.jack_studs[0].width / 2
            cull_inner_edge[1] -= opening.jack_studs[0].width / 2
        else:
            cull_inner_edge = cull_outer_edge
            cull_inner_edge[0] += opening.king_studs[0].width / 2
            cull_inner_edge[1] -= opening.king_studs[0].width / 2
        cull_outer_edge[0] -= opening.king_studs[0].width / 2
        cull_outer_edge[1] += opening.king_studs[0].width / 2
        to_cull = []
        to_split = []
        for stud in slab_populator.get_elements_by_category("stud"):
            beam_dot = dot_vectors(slab_populator._slab.frame.xaxis, Vector.from_start_end(slab_populator._slab.frame.point, stud.centerline.start))
            if beam_dot < cull_outer_edge[0] - stud.width or beam_dot > cull_outer_edge[1] + stud.width:  # outside culling domain
                continue
            if beam_dot > cull_inner_edge[0] + stud.width and beam_dot < cull_inner_edge[1] - stud.width:  # inside splitting domain
                to_split.append(stud)
                continue
            if do_segments_overlap(stud.centerline, opening.king_studs[0].centerline):
                to_cull.append(stud)
        return to_split, to_cull


class WindowDetailBase(OpeningDetailBase):
    """Base class for window opening detail sets.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    def create_elements(self, opening, slab_populator):
        """Generate the beams for a main interface."""
        frame_polyline = self._create_frame_polyline(opening, slab_populator)
        segments = [line for line in frame_polyline.lines]
        for i in range(4):
            if dot_vectors(segments[i].direction, slab_populator.stud_direction) < 0:
                segments[i] = Line(segments[i].end, segments[i].start)  # reverse the segment to match the stud direction
        opening.beams.append(self.beam_from_category(segments[1], "header", slab_populator, opening_edge_index=1))
        opening.beams.append(self.beam_from_category(segments[2], "king_stud", slab_populator, opening_edge_index=2))
        opening.beams.append(self.beam_from_category(segments[0], "king_stud", slab_populator, opening_edge_index=0))
        opening.beams.append(self.beam_from_category(segments[3], "sill", slab_populator, opening_edge_index=3))
        for beam in opening.beams:
            vector = get_polyline_segment_perpendicular_vector(frame_polyline, beam.attributes["opening_edge_index"])
            beam.frame.translate(vector * beam.width * 0.5)
        slab_populator.elements.extend(opening.beams)
        return opening.beams

    def create_joints(self, opening, slab_populator):
        """Generate the joints for WindowDetailB."""
        joints = []
        joints.extend([self.get_direct_rule_from_elements(opening.header, king, self.rules) for king in opening.king_studs])
        joints.extend(self._join_king_studs(opening, slab_populator))
        slab_populator.direct_rules.extend(joints)
        return joints


class WindowDetailA(WindowDetailBase):
    """Detail set for window openings without lintel posts.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    RULES = [
        CategoryRule(TButtJoint, "header", "king_stud"),
        CategoryRule(TButtJoint, "sill", "king_stud"),
        CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "king_stud", "sill"),
    ]

    def create_joints(self, opening, slab_populator):
        """Generate the beams for a cross interface."""
        joints = WindowDetailBase.create_joints(opening, slab_populator)
        joints.extend([self.get_joint_from_elements(opening.header, king, self.rules) for king in opening.king_studs])
        joints.extend([self.get_joint_from_elements(opening.sill, king, self.rules) for king in opening.king_studs])
        joints.append(self._join_king_studs(opening, slab_populator))
        slab_populator.direct_rules.extend(joints)
        return joints


class WindowDetailB(WindowDetailBase):
    """Detail set for window openings with lintel posts."""

    RULES = [
        CategoryRule(TButtJoint, "header", "king_stud"),
        CategoryRule(TButtJoint, "sill", "jack_stud"),
        CategoryRule(LButtJoint, "jack_stud", "header"),
        CategoryRule(TButtJoint, "jack_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "king_stud", "sill"),
    ]

    def create_elements(self, opening, slab_populator):
        """Generate the beams for a main interface."""
        super(WindowDetailB, self).create_elements(opening, slab_populator)
        self._add_jack_studs(opening, slab_populator)
        slab_populator.elements.extend(opening.beams)
        return opening.beams

    def create_joints(self, opening, slab_populator):
        """Generate the joints for WindowDetailB."""
        direct_rules = WindowDetailBase.create_joints(opening, slab_populator)
        direct_rules.extend([self.get_joint_from_elements(opening.sill, jack, self.rules) for jack in opening.jack_studs])
        direct_rules.extend([self.get_joint_from_elements(jack, opening.header, self.rules) for jack in opening.jack_studs])
        direct_rules.extend(self._join_jack_studs(opening, slab_populator))
        direct_rules.extend(self._join_king_studs(opening, slab_populator))
        slab_populator.direct_rules.extend(direct_rules)
        return direct_rules


class DoorDetailBase(OpeningDetailBase):
    """Base class for door opening detail sets.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    BEAM_CATEGORY_NAMES = ["header", "king_stud", "jack_stud"]

    def create_elements(self, opening, slab_populator):
        """Generate the beams for a main interface."""
        frame_polyline = self._create_frame_polyline(opening, slab_populator)
        segments = [line for line in frame_polyline.lines]
        for i in range(4):
            if dot_vectors(segments[i].direction, slab_populator.stud_direction) < 0:
                segments[i] = Line(segments[i].end, segments[i].start)  # reverse the segment to match the stud direction
        opening.beams.append(self.beam_from_category(segments[1], "header", slab_populator, opening_edge_index=1))
        opening.beams.append(self.beam_from_category(segments[2], "king_stud", slab_populator, opening_edge_index=2))
        opening.beams.append(self.beam_from_category(segments[0], "king_stud", slab_populator, opening_edge_index=0))
        for beam in opening.beams:
            vector = get_polyline_segment_perpendicular_vector(frame_polyline, beam.attributes["opening_edge_index"])
            beam.frame.translate(vector * beam.width * 0.5)
        self._apply_plate_contour(opening, slab_populator)
        return opening.beams

    def _apply_plate_contour(self, opening, slab_populator):
        """Apply the plate contour to the given slab populator."""
        outline = self._get_adjusted_door_outline(opening, slab_populator)
        for plate in slab_populator.plates:
            feature = FreeContour.from_polyline_and_element(outline, plate)
            plate.add_feature(feature)


    def _get_adjusted_door_outline(self, opening, slab_populator):
        """Adjust the door outline for the given opening."""
        outline = Polyline([p for p in opening.outline])
        slab_index = self._get_slab_segment_index(slab_populator._slab, outline)
        if slab_index is None:
            raise ValueError("Door outline does not intersect with the slab outline.")
        door_index = self._get_door_segment_index(outline, slab_populator.outline_a.lines[slab_index])
        vector = slab_populator.edge_perpendicular_vectors[slab_index]
        seg_a = slab_populator.outline_a.lines[slab_index]
        seg_b = slab_populator.outline_b.lines[slab_index]
        if dot_vectors(vector, seg_a.start) > dot_vectors(vector, seg_b.start):
            plane = Plane(seg_a.start, vector)
        else:
            plane = Plane(seg_b.end, vector)
        move_polyline_segment_to_plane(outline, door_index, plane)
        return outline


    def _get_slab_segment_index(self, slab_populator, polyline):
        """Get the index of the segment in the slab outline where the door is located."""
        for pl in slab_populator.outlines:
            for i, segment_a in enumerate(pl.lines):
                for segment_b in polyline.lines:
                    if intersection_segment_segment(segment_a, segment_b)[0]:
                        return i
        return None


    def _get_door_segment_index(self, polyline, segment):
        """Get the index of the door outline segment that lies on the slab edge."""
        lines = [line for line in polyline.lines]
        sorted_lines = sorted(lines, key=lambda x: distance_point_line(x.midpoint, segment))
        return lines.index(sorted_lines[0])


    def _split_edge_beam(self, opening, slab_populator):
        """Split the edge beam for door openings."""

        slab_index = self._get_slab_segment_index(slab_populator, opening.frame_polyline)
        if slab_index is None:
            raise ValueError("Door outline does not intersect with the slab outline.")
        door_index = self._get_door_segment_index(opening.frame_polyline, slab_populator.outline_a.lines[slab_index])

        edge_beam = slab_populator.edge_beams[slab_index][-1]
        outline_edge = opening.frame_polyline.lines[door_index]
        overlap = get_segment_overlap(edge_beam.centerline, outline_edge)

        if overlap[0] is None:
            raise ValueError("Edge beam does not intersect with the door outline.")

        if not (overlap[0] > 0 and overlap[1] < edge_beam.length):
            raise ValueError("Door outline must lay within the limits of a single slab edge.")

        beams = split_beam_at_lengths(edge_beam, [overlap[0], overlap[1]])

        slab_populator.edge_beams[slab_index].append(beams[2])


class DoorDetailAA(DoorDetailBase):
    """Detail set for door openings without lintel posts and without splitting the bottom plate."""

    RULES = [
        CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "header", "king_stud"),
    ]


class DoorDetailAB(DoorDetailBase):
    """Detail set for door openings without lintel posts and with splitting the bottom plate."""

    RULES = [
        CategoryRule(LButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "header", "king_stud"),
    ]

    def create_elements(self, opening, slab_populator):
        """Generate the beams for a main interface."""
        super(DoorDetailAB, self).create_elements(opening, slab_populator)
        self._split_edge_beam(opening, slab_populator)
        slab_populator.elements.extend(opening.beams)
        return opening.beams


class DoorDetailBA(DoorDetailBase):
    """Detail set for door openings with lintel posts and without splitting the bottom plate."""

    RULES = [
        CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "header", "king_stud"),
    ]

    def create_elements(self, opening, slab_populator):
        """Generate the beams for a main interface."""
        super(DoorDetailBA, self).create_elements(opening, slab_populator)
        self._add_jack_studs(opening, slab_populator)
        slab_populator.elements.extend(opening.beams)
        return opening.beams


class DoorDetailBB(DoorDetailBase):
    """Detail set for door openings with lintel posts and with splitting the bottom plate."""

    RULES = [
        CategoryRule(TButtJoint, "header", "king_stud"),
        CategoryRule(LButtJoint, "jack_stud", "header"),
        CategoryRule(LButtJoint, "jack_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
    ]

    def create_elements(self, opening, slab_populator):
        """Generate the beams for a main interface."""
        super(DoorDetailBB, self).create_elements(opening, slab_populator)
        self._add_jack_studs(opening, slab_populator)
        self._split_edge_beam(opening, slab_populator)
        slab_populator.elements.extend(opening.beams)
        return opening.beams
