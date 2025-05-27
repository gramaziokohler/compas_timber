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



class PlateToPlateInterface(object):
    """
    interface : :class:`compas.geometry.Polyline`
        The outline of the interface area.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface area.
        xaxis : interface normal (towards other plate)
        yaxis : up along the interface side
        normal: width direction, perpendicular to the interface

    """

    def __init__(self, interface_polyline, frame, interface_role, topology):
        self.interface_polyline = interface_polyline
        self.frame = frame
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

    Parameters
    ----------
    plate_a : :class:`compas_timber.elements.Plate`
        The first plate.
    plate_b : :class:`compas_timber.elements.Plate`
        The second plate.
    topology : literal(JointTopology)
        The topology in which the plates are connected.

    Attributes
    ----------
    plates : tuple of :class:`compas_timber.elements.Plate`
        The plates that are connected.
    plate_a_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_a where it meets plate_b.
    plate_b_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_b where it meets plate_a.

    """

    @property
    def __data__(self):
        data = super(PlateJoint, self).__data__
        data["main_plate_guid"] = self._main_plate_guid
        data["cross_plate_guid"] = self._cross_plate_guid
        data["topology"] = self.topology
        data["main_segment_index"] = self.main_segment_index
        data["cross_segment_index"] = self.cross_segment_index
        return data

    def __init__(self, topology_result, **kwargs):
        super(PlateJoint, self).__init__(**kwargs)
        self.topology = topology_result[0]
        self.main_plate = topology_result[1][0]
        self.main_segment_index = topology_result[1][1]
        self.cross_plate = topology_result[2][0]
        self.cross_segment_index = topology_result[2][1]
        self._main_plate_interface = None
        self._cross_plate_interface = None


        self._main_plate_guid = kwargs.get("main_plate_guid", None) or str(self.main_plate.guid)  # type: ignore
        self._cross_plate_guid = kwargs.get("cross_plate_guid", None) or str(self.cross_plate.guid)  # type: ignore

        if self.main_plate and self.cross_plate:
            self.reorder_planes_and_outlines()
            self._adjust_plate_outlines()

    def __repr__(self):
        return "PlateJoint({0}, {1}, {2})".format(self.main_plate, self.cross_plate, JointTopology.get_name(self.topology))


    @property
    def plates(self):
        return self.elements

    @property
    def elements(self):
        return self.main_plate, self.cross_plate

    @property
    def geometry(self):
        assert self.main_plate_interface
        return self.main_plate_interface.interface_polyline

    @property
    def main_interface_polyline(self):
        """The interface of the main plate."""
        return Polyline([self.main_outlines[0][self.main_segment_index],
        self.main_outlines[0][self.main_segment_index+1],
        self.main_outlines[1][self.main_segment_index+1],
        self.main_outlines[1][self.main_segment_index],
        self.main_outlines[0][self.main_segment_index]])

    @property
    def cross_interface_polyline(self):
        return Polyline([self.main_outlines[1][self.main_segment_index],
        self.main_outlines[1][self.main_segment_index+1],
        self.main_outlines[0][self.main_segment_index+1],
        self.main_outlines[0][self.main_segment_index],
        self.main_outlines[1][self.main_segment_index]])


    @property
    def interfaces(self):
        return self.main_plate_interface, self.cross_plate_interface

    @classmethod
    def create(cls, model, plates, **kwargs):
        # TODO: this is just a placeholder. The actual creation logic should be implemented.
        pass


    def get_interface_for_plate(self, plate):
        if plate is self.main_plate:
            return self.main_plate_interface
        elif plate is self.cross_plate:
            return self.cross_plate_interface
        else:
            raise ValueError("Plate not part of this joint.")

    def reorder_planes_and_outlines(self):
        if dot_vectors(self.cross_plate.frame.normal, PlateJoint.get_polyline_segment_perpendicular_vector(self.main_plate.outline_a, self.main_segment_index)) < 0:
            self.cross_planes = self.cross_plate.planes[::-1]
            self.cross_outlines = self.cross_plate.outlines[::-1]
        else:
            self.cross_planes = self.cross_plate.planes
            self.cross_outlines = self.cross_plate.outlines

        self.main_planes = self.main_plate.planes
        self.main_outlines = self.main_plate.outlines
        if self.topology == JointTopology.TOPO_L:
            if dot_vectors(self.main_plate.frame.normal, PlateJoint.get_polyline_segment_perpendicular_vector(self.cross_plate.outline_a, self.cross_segment_index)) < 0:
                self.main_planes = self.main_plate.planes[::-1]
                self.main_outlines = self.main_plate.outlines[::-1]



    @property
    def main_plate_interface(self):
        if not self._main_plate_interface:
            frame = Frame.from_points(self.main_interface_polyline.points[0], self.main_interface_polyline.points[1], self.main_interface_polyline.points[-2])
            if dot_vectors(frame.normal, Vector.from_start_end(self.cross_planes[1].point, self.cross_planes[0].point)) < 0:
                frame = Frame.from_points(self.main_interface_polyline.points[1], self.main_interface_polyline.points[0], self.main_interface_polyline.points[2])
            self._main_plate_interface = PlateToPlateInterface(
                self.main_interface_polyline,
                frame,
                InterfaceRole.MAIN,
                self.topology,
            )
        return self._main_plate_interface


    @property
    def cross_plate_interface(self):
        if not self._cross_plate_interface:
            frame = Frame.from_points(self.cross_interface_polyline.points[0], self.cross_interface_polyline.points[1], self.cross_interface_polyline.points[-2])
            if dot_vectors(frame.normal, Vector.from_start_end(self.cross_planes[0].point, self.cross_planes[1].point)) < 0:
                frame = Frame.from_points(self.cross_interface_polyline.points[1], self.cross_interface_polyline.points[0], self.cross_interface_polyline.points[2])
            self._cross_plate_interface = PlateToPlateInterface(
                self.cross_interface_polyline,
                frame,
                InterfaceRole.CROSS,
                self.topology,
            )
        return self._cross_plate_interface




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
        if PlateJoint.is_point_in_polyline(point, polyline):
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
        self.restore_plates_from_keys(*args, **kwargs)

    def restore_plates_from_keys(self, model):
        self.main_plate = model.element_by_guid(self._main_plate_guid)
        self.cross_plate = model.element_by_guid(self._cross_plate_guid)
        self._calculate_interfaces()

    def flip_roles(self):
        self.main_plate, self.cross_plate = self.cross_plate, self.main_plate
        self._main_plate_guid, self._cross_plate_guid = self._cross_plate_guid, self._main_plate_guid
        self._calculate_interfaces()

    def add_features(self):
        pass
