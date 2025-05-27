from compas.geometry import intersection_line_plane

from .joint import JointTopology
from .plate_joint import PlateJoint


class PlateMiterJoint(PlateJoint):
    """Creates a mitered edge plate-to-plate connection."""

    def __repr__(self):
        return "PlateMiterJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""

        assert self.plate_a
        assert self.plate_b

        for polyline, plane in zip(self.a_outlines, self.b_planes):
            for i, index in enumerate(
                [self.a_segment_index - 1, (self.a_segment_index + 1) % len(self.plate_a.outline_a.lines)]
            ):  # for each adjacent segment in the plate_a outline
                seg = polyline.lines[index]  # get the segment
                pt = intersection_line_plane(seg, plane)
                if pt:
                    if i == 0:
                        polyline[self.a_segment_index] = pt
                        if self.a_segment_index == 0:
                            polyline[-1] = pt
                    else:
                        polyline[self.a_segment_index + 1] = pt
                        if self.a_segment_index + 1 == len(polyline.lines):
                            polyline[0] = pt

            for polyline, plane in zip(self.b_outlines, self.a_planes):
                for i, index in enumerate(
                    [self.b_segment_index - 1, (self.b_segment_index + 1) % len(self.plate_b.outline_a.lines)]
                ):  # for each adjacent segment in the plate_a outline
                    seg = polyline.lines[index]  # get the segment
                    pt = intersection_line_plane(seg, plane)
                    if pt:
                        if i == 0:
                            polyline[self.b_segment_index] = pt
                            if self.b_segment_index == 0:
                                polyline[-1] = pt
                        else:
                            polyline[self.b_segment_index + 1] = pt
                            if self.b_segment_index + 1 == len(polyline.lines):
                                polyline[0] = pt
