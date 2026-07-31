from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import intersection_line_line

from compas_timber.elements import Beam
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import Slot

from .joint import Joint
from .utilities import beam_ref_side_incidence


class StekoJoint(Joint):
    """
    Steko Joint connecting beam to column
    """

    @property
    def __data__(self):
        data = super().__data__
        data["steko_column_guid"] = self.steko_column_guid
        data["steko_beams_guids"] = self.steko_beams_guids
        return data

    def __init__(self, steko_column: Beam, *steko_beams: Beam, **kwargs):
        super().__init__(
            elements=(steko_beams + (steko_column,)),
            **kwargs,
        )
        self.steko_column = steko_column
        self.steko_beams = list(steko_beams)
        self.slot_width = 0.04
        self.slot_depth = 0.4
        self.slot_padding = 0.04
        self.steko_column_guid = kwargs.get("steko_column_guid", None) or str(steko_column.guid)
        self.steko_beams_guids = kwargs.get("steko_beams_guids", None) or [str(beam.guid) for beam in steko_beams]

    @property
    def location(self) -> Point:
        point = Point(*intersection_line_line(self.steko_column.centerline, self.steko_beams[0].centerline)[0])
        return point

    @property
    def beams(self) -> list[Beam]:
        return [self.steko_column] + self.steko_beams

    def column_beam_ref_side_index(self, beam):
        ref_side_dict = beam_ref_side_incidence(beam, self.steko_column, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def beam_ref_side_index(self, beam, ref_beam):
        ref_side_dict = beam_ref_side_incidence(ref_beam, beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    def add_extensions(self):
        for beam in self.steko_beams:
            ref_side_dict = beam_ref_side_incidence(beam, self.steko_column, ignore_ends=True)
            cross_beam_ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
            cutting_plane = self.steko_column.ref_sides[cross_beam_ref_side_index]

            start, end = beam.extension_to_plane(cutting_plane)
            extension_tolerance = 0.01
            joint_id = self.guid
            beam.add_blank_extension(start + extension_tolerance, end + extension_tolerance, joint_id)

    def add_features(self):

        for beam in self.steko_beams:
            # Jack Rafter Cut
            plane = Plane.from_frame(self.steko_column.ref_sides[self.column_beam_ref_side_index(beam)])
            plane.normal *= -1
            jrc = JackRafterCutProxy.from_plane_and_beam(plane, beam)
            beam.add_feature(jrc)
            self.features.append(jrc)

            # Slots
            plane_normal = Vector(*cross_vectors(beam.frame.xaxis, self.steko_column.frame.xaxis))
            plane = Plane(self.location, plane_normal)
            a_plane = plane.translated(plane_normal * (beam.width / 2 - self.slot_padding - self.slot_width / 2))
            slot = Slot.from_plane_and_beam(a_plane, beam, depth=self.slot_depth, thickness=self.slot_width)
            beam.add_feature(slot)
            b_plane = plane.translated(plane_normal * -(beam.width / 2 - self.slot_padding - self.slot_width / 2))
            slot = Slot.from_plane_and_beam(b_plane, beam, depth=self.slot_depth, thickness=self.slot_width)
            beam.add_feature(slot)

            # Drillings
            x_dir = Vector.from_start_end(self.location, beam.centerline.midpoint).unitized()
            y_dir = Vector(0, 0, 1)
            line = Line.from_point_direction_length(self.location, plane_normal, beam.width + 0.1)
            line.translate(plane_normal * -0.05)
            line.translate(plane_normal * -beam.width / 2)
            line.translate(x_dir * (self.steko_column.width / 2 + 0.04))
            line.translate(y_dir * -(beam.height / 2 - 0.04))
            lines = []
            x_gap = (self.slot_depth - 0.08) / 2
            y_gap = (beam.height - 0.08) / 4
            for x in range(3):
                for y in range(5):
                    drill_line = line.copy()
                    drill_line.translate(x_dir * x * x_gap)
                    drill_line.translate(y_dir * y * y_gap)
                    drilling = Drilling.from_line_and_element(drill_line, beam, diameter=0.02)
                    beam.add_feature(drilling)
                    self.features.append(drilling)
                    lines.append(drill_line)
