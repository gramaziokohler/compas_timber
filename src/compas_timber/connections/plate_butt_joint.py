from compas.geometry import intersection_line_plane

from .joint import JointTopology
from .plate_joint import PlateJoint


class PlateButtJoint(PlateJoint):
    """Creates a plate-to-plate butt-joint connection."""

    @property
    def __data__(self):
        data = super(PlateJoint, self).__data__
        data["main_plate_guid"] = self._main_plate_guid
        data["cross_plate_guid"] = self._cross_plate_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, main_plate, cross_plate, topology, main_segment_index, cross_segment_index, **kwargs):
        super(PlateButtJoint, self).__init__(main_plate, cross_plate, topology, main_segment_index, cross_segment_index, **kwargs)

    @property
    def main_plate(self):
        """Return the main plate."""
        return self.plate_a

    @property
    def cross_plate(self):
        """Return the cross plate."""
        return self.plate_b

    @property
    def main_segment_index(self):
        """Return the index of the segment in the main plate outline."""
        return self.a_segment_index

    @property
    def cross_segment_index(self):
        """Return the index of the segment in the main plate outline."""
        return self.b_segment_index

    @property
    def _main_plate_guid(self):
        """Return the GUID of the main plate."""
        return self.plate_a.guid if self.plate_a else None

    @property
    def _cross_plate_guid(self):
        """Return the GUID of the cross plate."""
        return self.plate_b.guid if self.plate_b else None

    @property
    def main_planes(self):
        """Return the ordered planes of the main plate."""
        return self.a_planes

    @property
    def cross_planes(self):
        """Return the ordered planes of the cross plate."""
        return self.b_planes

    @property
    def main_outlines(self):
        """Return the ordered outlines of the main plate."""
        return self.a_outlines

    @property
    def cross_outlines(self):
        """Return the ordered outlines of the cross plate."""
        return self.b_outlines

    def __repr__(self):
        return "PlateButtJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))

    def _adjust_plate_outlines(self):
        """Adjust the outlines of the plates to match the joint."""

        assert self.main_plate
        assert self.cross_plate

        for polyline in self.main_outlines:
            for i, index in enumerate(
                [self.main_segment_index - 1, (self.main_segment_index + 1) % len(self.main_plate.outline_a.lines)]
            ):  # for each adjacent segment in the main plate outline
                seg = polyline.lines[index]  # get the segment
                pt = intersection_line_plane(seg, self.cross_planes[0])
                if pt:
                    if i == 0:
                        polyline[self.main_segment_index] = pt
                        if self.main_segment_index == 0:
                            polyline[-1] = pt
                    else:
                        polyline[self.main_segment_index + 1] = pt
                        if self.main_segment_index + 1 == len(polyline.lines):
                            polyline[0] = pt

        if self.topology == JointTopology.TOPO_L:
            for polyline in self.cross_outlines:
                for i, index in enumerate(
                    [self.cross_segment_index - 1, (self.cross_segment_index + 1) % len(self.cross_plate.outline_a.lines)]
                ):  # for each adjacent segment in the main plate outline
                    seg = polyline.lines[index]  # get the segment
                    pt = intersection_line_plane(seg, self.main_planes[1])
                    if pt:
                        if i == 0:
                            polyline[self.cross_segment_index] = pt
                            if self.cross_segment_index == 0:
                                polyline[-1] = pt
                        else:
                            polyline[self.cross_segment_index + 1] = pt
                            if self.cross_segment_index + 1 == len(polyline.lines):
                                polyline[0] = pt
