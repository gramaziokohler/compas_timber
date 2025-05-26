from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Polygon
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import dot_vectors
from compas.geometry import cross_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_polyline_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_segment_polyline
from compas.geometry import is_colinear_line_line
from compas.geometry import is_point_in_polygon_xy
from compas.geometry import Transformation
from compas.itertools import pairwise
from compas.tolerance import TOL

from .joint import Joint
from .joint import JointTopology


class InterfaceRole(object):
    """
    Enumeration of the possible interface roles.

    Attributes
    ----------
    MAIN : literal(0)
        The interface is the main interface.
    CROSS : literal(1)
        The interface is the cross interface.
    """

    MAIN = "MAIN"
    CROSS = "CROSS"



class SlabToSlabInterface(object):
    """
    interface : :class:`compas.geometry.Polyline`
        The outline of the interface area.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface area.
        xaxis : interface normal (towards other slab)
        yaxis : up along the interface side
        normal: width direction, perpendicular to the interface

    """

    def __init__(self, interface_polyline, frame, interface_type, interface_role, topology):
        self.interface_polyline = interface_polyline
        self.frame = frame
        self.interface_type = interface_type
        self.interface_role = interface_role
        self.topology = topology  # TODO: don't like this here

    def __repr__(self):
        return "PlateToPlateInterface({0}, {1}, {2})".format(
            self.interface_type,
            self.interface_role,
            JointTopology.get_name(self.topology),
        )

    def as_plane(self):
        """Returns the interface as a plane.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The plane of the interface.
        """
        return Plane.from_three_points(*self.interface_polyline.points[:3])


class PlateJoint(Joint):
    """Models a plate to plate interaction.

    TODO:First in a very minimal way until we know where this is going.


    Parameters
    ----------
    plate_a : :class:`compas_timber.elements.Slab`
        The first plate.
    plate_b : :class:`compas_timber.elements.Slab`
        The second plate.
    topology : literal(JointTopology)
        The topology in which the plates are connected.

    Attributes
    ----------
    slabs : tuple of :class:`compas_timber.elements.Slab`
        The slabs that are connected.
    slab_a_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of slab_a where it meets slab_b.
    slab_b_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of slab_b where it meets slab_a.

    """

    @property
    def __data__(self):
        data = super(SlabJoint, self).__data__
        data["main_slab_guid"] = self._main_slab_guid
        data["cross_slab_guid"] = self._cross_slab_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, topology_result, **kwargs):
        super(SlabJoint, self).__init__(**kwargs)
        self.topology = topology_result[0]
        self.main_slab = topology_result[1][0]
        self.main_segment_index = topology_result[1][2]
        self.cross_slab = topology_result[2][0]
        self.cross_segment_index = topology_result[2][2]


        self._main_slab_guid = kwargs.get("main_slab_guid", None) or str(self.main_slab.guid)  # type: ignore
        self._cross_slab_guid = kwargs.get("cross_slab_guid", None) or str(self.cross_slab.guid)  # type: ignore

        if self.main_slab and self.cross_slab:
            self.reorder_planes_and_outlines()
            self._adjust_slab_outlines()

    def __repr__(self):
        return "SlabJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))

    @property
    def slabs(self):
        return self.elements

    @property
    def elements(self):
        return self.main_slab, self.cross_slab

    @property
    def geometry(self):
        assert self.main_slab_interface
        return self.main_slab_interface.interface_polyline

    @property
    def main_slab_interface(self):
        """The interface of the main slab."""
        return Polyline([self.main_slab.outline_a[self.main_segment_index],
        self.main_slab.outline_a[self.main_segment_index+1],
        self.main_slab.outline_b[self.main_segment_index+1],
        self.main_slab.outline_b[self.main_segment_index],
        self.main_slab.outline_a[self.main_segment_index]])

    @property
    def cross_slab_interface(self):
        points = []
        if self.topology == JointTopology.TOPO_L:
            for index in [self.cross_segment_index-1, (self.cross_segment_index+1)% len(self.cross_slab.outline_a.lines)]:
                seg = self.cross_outlines[0].lines[index]
                for plane in self.main_slab.planes:
                    pt =  intersection_line_plane(seg, plane)
                    if pt:
                        points.append(pt)
        else:
            for plane in self.main_slab.planes:
                pts = intersection_polyline_plane(self.cross_outlines[0], plane)
                print("pts: ", pts)
                if len(pts) == 2:
                    points.extend(pts)
        return Polyline([points[0], points[1], points[3], points[2], points[0]])


    @property
    def interfaces(self):
        return self.main_slab_interface, self.cross_slab_interface

    def get_interface_for_slab(self, slab):
        if slab is self.main_slab:
            return self.main_slab_interface
        elif slab is self.cross_slab:
            return self.cross_slab_interface
        else:
            raise ValueError("Slab not part of this joint.")

    def reorder_planes_and_outlines(self):
        if dot_vectors(self.cross_slab.frame.normal, SlabJoint.get_polyline_segment_perpendicular_vector(self.main_slab.outline_a, self.main_segment_index)) < 0:
            self.cross_planes = self.cross_slab.planes[::-1]
            self.cross_outlines = self.cross_slab.outlines[::-1]
        else:
            self.cross_planes = self.cross_slab.planes
            self.cross_outlines = self.cross_slab.outlines

        self.main_planes = self.main_slab.planes
        self.main_outlines = self.main_slab.outlines
        if self.topology == JointTopology.TOPO_L:
            if dot_vectors(self.main_slab.frame.normal, SlabJoint.get_polyline_segment_perpendicular_vector(self.cross_slab.outline_a, self.cross_segment_index)) < 0:
                self.main_planes = self.main_slab.planes[::-1]
                self.main_outlines = self.main_slab.outlines[::-1]




    def _adjust_slab_outlines(self):
        """Adjust the outlines of the slabs to match the joint."""

        assert self.main_slab
        assert self.cross_slab


        for polyline in self.main_outlines:
            for i, index in enumerate([self.main_segment_index-1, (self.main_segment_index+1)% len(self.main_slab.outline_a.lines)]):      #for each adjacent segment in the main slab outline
                seg = polyline.lines[index] # get the segment
                pt = intersection_line_plane(seg, self.cross_planes[0])
                if pt:
                    if i == 0:
                        polyline[self.main_segment_index] = pt
                        if self.main_segment_index == 0:
                            polyline[-1] = pt
                    else:
                        polyline[self.main_segment_index+1] = pt
                        if self.main_segment_index+1 == len(polyline.lines):
                            polyline[0] = pt

        if self.topology == JointTopology.TOPO_L:
            for polyline in self.cross_outlines:
                for i, index in enumerate([self.cross_segment_index-1, (self.cross_segment_index+1)% len(self.cross_slab.outline_a.lines)]):      #for each adjacent segment in the main slab outline
                    seg = polyline.lines[index] # get the segment
                    pt = intersection_line_plane(seg, self.main_planes[1])
                    if pt:
                        if i == 0:
                            polyline[self.cross_segment_index] = pt
                            if self.cross_segment_index == 0:
                                polyline[-1] = pt
                        else:
                            polyline[self.cross_segment_index+1] = pt
                            if self.cross_segment_index+1 == len(polyline.lines):
                                polyline[0] = pt

    def _calculate_interfaces(self):
        return

        # self.main_slab_interface = SlabToSlabInterface(
        #     interface,
        #     Frame(interface[0], interface_normal, up_vector),
        #     main_interface_type,
        #     InterfaceRole.MAIN,
        #     self.topology,
        # )
        # self.cross_slab_interface = SlabToSlabInterface(
        #     interface,
        #     Frame(interface[1], interface_normal.inverted(), up_vector.inverted()),
        #     cross_interface_type,
        #     InterfaceRole.CROSS,
        #     self.topology,
        # )




    @staticmethod
    def find_colinear_segment(polyline, lines):
        for i, seg in enumerate(polyline.lines):
            for line in lines:
                if is_colinear_line_line(seg, line):
                    return i
        return None


    @staticmethod
    def get_polyline_segment_perpendicular_vector(polyline, segment_index):
        """Get the vector perpendicular to a polyline segment. This vector points outside of the polyline.
        The polyline must be closed.

        Parameters
        ----------
        polyline : :class:`compas.geometry.Polyline`
            The polyline to check. Must be closed.
        segment_index : int
            The index of the segment in the polyline.

        Returns
        -------
        int
            The index of the point in the polyline, or None if not found.
        """
        plane = Plane.from_points(polyline.points)
        pt = polyline.lines[segment_index].point_at(0.5)
        perp_vector = Vector(*cross_vectors(polyline.lines[segment_index].direction, plane.normal))
        point = pt + (perp_vector * 0.1)
        if SlabJoint.is_point_in_polyline(point, polyline):
            return Vector.from_start_end(point, pt)
        return Vector.from_start_end(pt, point)


    @staticmethod
    def is_point_in_polyline(point, polyline):
        """Check if a point is inside a polyline. Polyline must be closed.

        Parameters
        ----------
        point : :class:`compas.geometry.Point`
            The point to check.
        polyline : :class:`compas.geometry.Polyline`
            The polyline to check against.

        Returns
        -------
        bool
            True if the point is inside the polyline, False otherwise.
        """
        frame = Frame.from_points(*polyline.points[:3])
        xform = Transformation.from_frame_to_frame(frame, Frame.worldXY())
        pgon = Polygon([pt.transformed(xform) for pt in polyline.points[:-1]])
        pt = point.transformed(xform)
        return TOL.is_close(pt[2], 0.0) and is_point_in_polygon_xy(pt, pgon)


    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_slabs_from_keys(*args, **kwargs)

    def restore_slabs_from_keys(self, model):
        self.main_slab = model.element_by_guid(self._main_slab_guid)
        self.cross_slab = model.element_by_guid(self._cross_slab_guid)
        self._calculate_interfaces()

    def flip_roles(self):
        self.main_slab, self.cross_slab = self.cross_slab, self.main_slab
        self._main_slab_guid, self._cross_slab_guid = self._cross_slab_guid, self._main_slab_guid
        self._calculate_interfaces()

    def add_features(self):
        pass
