from compas.geometry import Box
from compas.geometry import Vector
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors

from compas_timber.design import CategoryRule
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import get_segment_overlap

from .slab_populator import beam_from_category
from .slab_populator import intersection_line_beams


class OpeningDetailBase(object):
    """Base class for opening detail sets.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """
    BEAM_CATEGORY_NAMES = ["header","sill","king_stud","jack_stud",]

    RULES = [
        CategoryRule(TButtJoint, "header", "king_stud"),
        CategoryRule(TButtJoint, "sill", "king_stud"),
        CategoryRule(TButtJoint, "sill", "jack_stud"),
        CategoryRule(LButtJoint, "jack_stud", "header"),
        CategoryRule(TButtJoint, "jack_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "king_stud", "sill"),
        CategoryRule(TButtJoint, "king_stud", "edge_stud"),
        CategoryRule(TButtJoint, "jack_stud", "edge_stud"),
    ]

    def __init__(self, beam_width_overrides=None, joint_rule_overrides=None):
        self.beam_width_overrides = beam_width_overrides
        self.joint_rule_overrides = joint_rule_overrides or []
        self._rules = []
        
    @property
    def rules(self):
        if not self._rules:
            self._rules = self.RULES
            for override in self.joint_rule_overrides:
                for rule in self.RULES:
                    if override.category_a == rule.category_a and override.category_b == rule.category_b:
                        rule = override
                        break
                else:
                    self._rules.append(override)
        return self._rules

        
    def _get_frame_polyline(opening, slab_populator):
        """Bounding rectangle aligned orthogonal to the slab.stud_direction."""

        frame = Frame(opening.outline[0], cross_vectors(slab_populator.stud_direction, slab_populator.normal), slab_populator.stud_direction)
        # Oriented bounding box of the window. used for creating framing elements around non-standard window shapes.
        rebase = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        box = Box.from_points(opening.outline.transformed(rebase))
        rebase.invert()
        box.transform(rebase)
        #opening.obb = box
        opening.frame_polyline = Polyline([box.corner(0), box.corner(1), box.corner(2), box.corner(3), box.corner(0)])
        return opening.frame_polyline


    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        return []

    @staticmethod
    def generate_joints(opening, slab_populator):
        """Generate the beams for a cross interface."""
        return []

    @classmethod
    def _join_king_studs(cls, opening, slab_populator):
        joints = []
        for king_stud in opening.king_studs:
            intersections = []
            # get beams to intersect with
            beams = []
            for val in slab_populator._edge_beams.values():
                beams.extend(val)
            for op in slab_populator.openings:
                if op != opening:
                    beams.extend([op.sill, op.header])
            # get intersections
            intersections = intersection_line_beams(king_stud.centerline, beams, max_distance=slab_populator.beam_dimensions["king_stud"][0])
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
            joints.append(slab_populator.get_joint_from_elements(king_stud, bottom_int["beam"], rules=cls.RULES))
            joints.append(slab_populator.get_joint_from_elements(king_stud, top_int["beam"], rules=cls.RULES))
        return joints

    @classmethod
    def _join_jack_studs(cls, opening, slab_populator):
        joints = []
        for jack_stud in opening.jack_studs:
            intersections = []
            # get beams to intersect with
            beams = []
            for val in slab_populator._edge_beams.values():
                beams.extend(val)
            for op in slab_populator.openings:
                if op != opening:
                    beams.extend([op.header])
            # get intersections
            intersections = intersection_line_beams(jack_stud.centerline, beams, max_distance=slab_populator.beam_dimensions["jack_stud"][0])
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
            joints.append(slab_populator.get_joint_from_elements(jack_stud, bottom_int["beam"], rules=cls.RULES))
        return joints

    @staticmethod
    def split_bottom_plate(slab_populator, sill):
        """Split the bottom plate beam for door openings."""
        for beam in slab_populator.bottom_plate_beams:
            overlap = get_segment_overlap(beam.centerline, sill.centerline)

            if overlap[0] is None:
                continue
            if not (overlap[0] > 0 and overlap[1] < beam.length):
                continue

            new_beam = beam.copy()
            new_beam.attributes.update(beam.attributes)
            new_beam.length = beam.length - overlap[1]
            beam.length = overlap[0]
            new_beam.frame.translate(beam.frame.xaxis * overlap[1])

            slab_populator._edge_beams[beam.attributes["edge_index"]].append(new_beam)
            break


    @staticmethod
    def cull_and_split_studs(opening, slab_populator):
        """Split the bottom plate beam for door openings."""
        cull_outer_edge = [dot_vectors(slab_populator.frame.xaxis, Vector.from_start_end(slab_populator.frame.point, king))for king in opening.king_studs]
        cull_outer_edge.sort()
        if opening.jack_beams:
            cull_inner_edge = [dot_vectors(slab_populator.frame.xaxis, Vector.from_start_end(slab_populator.frame.point, jack))for jack in opening.jack_beams]
            cull_inner_edge.sort()
            cull_inner_edge[0]+=opening.jack_studs[0].width
            cull_inner_edge[1]-=opening.jack_studs[0].width
        else:
            cull_inner_edge = cull_outer_edge
            cull_inner_edge[0]+=opening.king_studs[0].width
            cull_inner_edge[1]-=opening.king_studs[0].width
        cull_outer_edge[0]-=opening.king_studs[0].width
        cull_outer_edge[1]+=opening.king_studs[0].width



        to_cull = []
        for beam in slab_populator.studs:
            beam_dot = dot_vectors(slab_populator.frame.xaxis, Vector.from_start_end(slab_populator.frame.point, beam.centerline.start))
            if beam_dot < cull_outer_edge[0]-beam.width or beam_dot > cull_outer_edge[1]+beam.width: #within opening domain
                continue
            if beam_dot < cull_inner_edge[0]+beam.width or beam_dot > cull_inner_edge[1]-beam.width:
                to_cull.append(beam)
                continue            
            #now split remaining beams
            overlap = (
                dot_vectors(slab_populator.stud_direction, Vector.from_start_end(beam.centerline.start, opening.sill.centerline.start)), 
                dot_vectors(slab_populator.stud_direction, Vector.from_start_end(beam.centerline.start, opening.header.centerline.start)), 
                )
            if overlap[1]<0 or overlap[0] > beam.length:    #if sill is above top of stud or header is below bottom of stud
                continue            

            new_beam = beam.copy()
            new_beam.attributes.update(beam.attributes)
            new_beam.length = beam.length - overlap[1]
            beam.length = overlap[0]
            new_beam.frame.translate(beam.frame.xaxis * overlap[1])

            slab_populator._edge_beams[beam.attributes["edge_index"]].append(new_beam)
        for beam in to_cull:
            opening.studs.remove(beam)


class WindowDetailA(OpeningDetailBase):
    """Detail set for window openings without lintel posts.

    Parameters
    ----------
    interface : :class:`compas_timber.connections.SlabToSlabInterface`
        The interface for which the detail set is created.
    """

    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        frame_polyline = OpeningDetailBase._get_frame_polyline(opening, slab_populator)
        segments = [line for line in frame_polyline.lines]
        for i in range(4):
            if dot_vectors(segments[i].direction, slab_populator.stud_direction) < 0:
                segments[i] = Line(segments[i].end, segments[i].start)  # reverse the segment to match the stud direction
        opening.beams.append(beam_from_category(slab_populator, segments[1], "header", edge_index=1))
        opening.beams.append(beam_from_category(slab_populator, segments[2], "king_stud", edge_index=2))
        opening.beams.append(beam_from_category(slab_populator, segments[0], "king_stud", edge_index=0))
        opening.beams.append(beam_from_category(slab_populator, segments[3], "sill", edge_index=3))
        for beam in opening.beams:
            vector = get_polyline_segment_perpendicular_vector(frame_polyline, beam.attributes["edge_index"])
            beam.frame.translate(vector * beam.width * 0.5)
        return opening.beams

    @classmethod
    def generate_joints(cls, opening, slab_populator):
        """Generate the beams for a cross interface."""
        joints = []
        joints.extend([slab_populator.get_joint_from_elements(opening.header, king, cls.RULES) for king in opening.king_studs])
        joints.extend([slab_populator.get_joint_from_elements(opening.sill, king, cls.RULES) for king in opening.king_studs])
        joints.append(cls._join_king_studs(opening, slab_populator))
        return joints

class WindowDetailB(WindowDetailA):
    """Detail set for window openings with lintel posts."""

    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        frame_polyline = OpeningDetailBase._get_frame_polyline(opening, slab_populator)
        beams = WindowDetailA.generate_elements(opening, slab_populator)
        opening.beams.append(beam_from_category(slab_populator, opening.king_studs[0].centerline, "jack_stud", edge_index=2, normal_offset=False))
        opening.beams.append(beam_from_category(slab_populator, opening.king_studs[1].centerline, "jack_stud", edge_index=0, normal_offset=False))
        opening.king_studs[0].frame.translate(
            get_polyline_segment_perpendicular_vector(frame_polyline, 2) * (slab_populator.beam_dimensions["jack_stud"][0] + slab_populator.beam_dimensions["king_stud"][0]) * 0.5
        )
        opening.king_studs[1].frame.translate(
            get_polyline_segment_perpendicular_vector(frame_polyline, 0) * (slab_populator.beam_dimensions["jack_stud"][0] + slab_populator.beam_dimensions["king_stud"][0]) * 0.5
        )

        return beams

    @classmethod
    def generate_joints(cls, opening, slab_populator):
        """Generate the joints for WindowDetailB."""
        joints = []
        joints.extend([slab_populator.get_joint_from_elements(opening.header, king, cls.RULES) for king in opening.king_studs])
        joints.extend([slab_populator.get_joint_from_elements(opening.sill, jack, cls.RULES) for jack in opening.jack_studs])
        joints.extend([slab_populator.get_joint_from_elements(jack, opening.header, cls.RULES) for jack in opening.jack_studs])
        joints.extend(cls._join_jack_studs(opening, slab_populator))
        joints.extend(cls._join_king_studs(opening, slab_populator))
        return joints


class DoorDetailAA(WindowDetailA):
    """Detail set for door openings without lintel posts and without splitting the bottom plate."""

    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        WindowDetailA.generate_elements(opening, slab_populator)
        opening.beams.remove(opening.sill)
        return opening.beams


class DoorDetailAB(WindowDetailA):
    """Detail set for door openings without lintel posts and with splitting the bottom plate."""

    RULES = [
        CategoryRule(TButtJoint, "header", "king_stud"),
        CategoryRule(TButtJoint, "sill", "king_stud"),
        CategoryRule(LButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "king_stud", "sill"),
    ]

    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        WindowDetailA.generate_elements(opening, slab_populator)
        sill = opening.sill
        opening.beams.remove(sill)
        OpeningDetailBase.split_bottom_plate(slab_populator, sill)
        return opening.beams


class DoorDetailBA(WindowDetailB):
    """Detail set for door openings with lintel posts and without splitting the bottom plate."""

    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        WindowDetailB.generate_elements(opening, slab_populator)
        sill = opening.sill
        opening.beams.remove(sill)
        return opening.beams


class DoorDetailBB(WindowDetailB):
    """Detail set for door openings with lintel posts and with splitting the bottom plate."""

    RULES = [
        CategoryRule(TButtJoint, "header", "king_stud"),
        CategoryRule(TButtJoint, "sill", "king_stud"),
        CategoryRule(TButtJoint, "sill", "jack_stud"),
        CategoryRule(LButtJoint, "jack_stud", "header"),
        CategoryRule(TButtJoint, "jack_stud", "bottom_plate_beam"),
        CategoryRule(LButtJoint, "king_stud", "bottom_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "top_plate_beam"),
        CategoryRule(TButtJoint, "king_stud", "header"),
        CategoryRule(TButtJoint, "king_stud", "sill"),
    ]

    @staticmethod
    def generate_elements(opening, slab_populator):
        """Generate the beams for a main interface."""
        WindowDetailB.generate_elements(opening, slab_populator)
        sill = opening.sill
        opening.beams.remove(sill)
        OpeningDetailBase.split_bottom_plate(slab_populator, sill)
        return opening.beams
