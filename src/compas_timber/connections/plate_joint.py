from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import dot_vectors

from compas_timber.utils import get_polyline_segment_perpendicular_vector

from .joint import Joint
from .joint import JointTopology
from .solver import ConnectionSolver


class InterfaceRole(object):
    """
    Enumeration of the possible interface roles.

    Attributes
    ----------
    MAIN : literal("MAIN")
        The interface is the main interface.
    CROSS : literal("CROSS")
        The interface is the cross interface.
    NONE : literal("NONE")
        The interface has no specific role. E.g. when a miter joint is used.
    """

    MAIN = "MAIN"
    CROSS = "CROSS"
    NONE = "NONE"


class PlateToPlateInterface(object):
    """
    interface_polyline : :class:`compas.geometry.Polyline`
        The outline of the interface area.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface area.
        xaxis : interface normal (towards other plate)
        yaxis : up along the interface side
        normal: width direction, perpendicular to the interface
    interface_role : literal(InterfaceRole)
        The role of the interface in the joint.
    topology : literal(JointTopology)
        The topology of the joint in which the interface is used.
        E.g. L or T

    """

    def __init__(self, interface_polyline, frame, interface_role, topology):
        self.interface_polyline = interface_polyline
        self.frame = frame
        self.interface_role = interface_role
        self.topology = topology  # TODO: don't like this here

    def __repr__(self):
        return "PlateToPlateInterface({0}, {1})".format(
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
    a_segment_index : int
        The index of the segment in plate_a's outline where the plates are connected.
    b_segment_index : int
        The index of the segment in plate_b's outline where the plates are connected.
    **kwargs : dict, optional
        Additional keyword arguments to pass to the parent class.

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
        data["plate_a_guid"] = self._plate_a_guid
        data["plate_b_guid"] = self._plate_b_guid
        data["topology"] = self.topology
        data["a_segment_index"] = self.a_segment_index
        data["b_segment_index"] = self.b_segment_index
        return data

    def __init__(self, plate_a=None, plate_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(PlateJoint, self).__init__(**kwargs)
        self.plate_a = plate_a
        self.plate_b = plate_b
        self.topology = topology
        self.a_segment_index = a_segment_index
        self.b_segment_index = b_segment_index
        self._plate_a_interface = None
        self._plate_b_interface = None

        self.a_outlines = None
        self.b_outlines = None
        self.a_planes = None
        self.b_planes = None

        self._plate_a_guid = kwargs.get("plate_a_guid", None) or str(self.plate_a.guid)  # type: ignore
        self._plate_b_guid = kwargs.get("plate_b_guid", None) or str(self.plate_b.guid)  # type: ignore

    def __repr__(self):
        return "PlateJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))

    @property
    def plates(self):
        return self.elements

    @property
    def elements(self):
        return self.plate_a, self.plate_b

    @property
    def geometry(self):
        assert self.plate_a_interface
        return self.plate_a_interface.interface_polyline

    @property
    def a_interface_polyline(self):
        """The interface of the a plate."""
        return Polyline(
            [
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index],
            ]
        )

    @property
    def b_interface_polyline(self):
        return Polyline(
            [
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index],
            ]
        )

    @property
    def interfaces(self):
        return self.plate_a_interface, self.plate_b_interface

    @property
    def plate_a_interface(self):
        if not self._plate_a_interface:
            frame = Frame.from_points(self.a_interface_polyline.points[0], self.a_interface_polyline.points[1], self.a_interface_polyline.points[-2])
            if dot_vectors(frame.normal, Vector.from_start_end(self.b_planes[1].point, self.b_planes[0].point)) < 0:
                frame = Frame.from_points(self.a_interface_polyline.points[1], self.a_interface_polyline.points[0], self.a_interface_polyline.points[2])
            self._plate_a_interface = PlateToPlateInterface(
                self.a_interface_polyline,
                frame,
                InterfaceRole.MAIN,
                self.topology,
            )
        return self._plate_a_interface

    @property
    def plate_b_interface(self):
        if not self._plate_b_interface:
            frame = Frame.from_points(self.b_interface_polyline.points[0], self.b_interface_polyline.points[1], self.b_interface_polyline.points[-2])
            if dot_vectors(frame.normal, Vector.from_start_end(self.b_planes[0].point, self.b_planes[1].point)) < 0:
                frame = Frame.from_points(self.b_interface_polyline.points[1], self.b_interface_polyline.points[0], self.b_interface_polyline.points[2])
            self._plate_b_interface = PlateToPlateInterface(
                self.b_interface_polyline,
                frame,
                InterfaceRole.CROSS,
                self.topology,
            )
        return self._plate_b_interface

    def add_features(self):
        """Add features to the plates based on the joint."""
        if self.plate_a and self.plate_b:
            if self.topology is None or (self.a_segment_index is None and self.b_segment_index is None):
                topo_results = ConnectionSolver.find_plate_plate_topology(self.plate_a, self.plate_b)
                if not topo_results:
                    raise ValueError("Could not determine topology for plates {0} and {1}.".format(self.plate_a, self.plate_b))
                self.topology = topo_results[0]
                self.a_segment_index = topo_results[1][1]
                self.b_segment_index = topo_results[2][1]
            self.reorder_planes_and_outlines()
            self._adjust_plate_outlines()
            self.plate_a.interfaces.append(self.plate_a_interface)
            self.plate_b.interfaces.append(self.plate_b_interface)

    def get_interface_for_plate(self, plate):
        if plate is self.plate_a:
            return self.plate_a_interface
        elif plate is self.plate_b:
            return self.plate_b_interface
        else:
            raise ValueError("Plate not part of this joint.")

    def reorder_planes_and_outlines(self):
        if dot_vectors(self.plate_b.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_a.outline_a, self.a_segment_index)) < 0:
            self.b_planes = self.plate_b.planes[::-1]
            self.b_outlines = self.plate_b.outlines[::-1]
        else:
            self.b_planes = self.plate_b.planes
            self.b_outlines = self.plate_b.outlines

        self.a_planes = self.plate_a.planes
        self.a_outlines = self.plate_a.outlines
        if self.topology == JointTopology.TOPO_L:
            if dot_vectors(self.plate_a.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_b.outline_a, self.b_segment_index)) < 0:
                self.a_planes = self.plate_a.planes[::-1]
                self.a_outlines = self.plate_a.outlines[::-1]

    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_plates_from_keys(*args, **kwargs)

    def restore_plates_from_keys(self, model):
        self.plate_a = model.element_by_guid(self._plate_a_guid)
        self.plate_b = model.element_by_guid(self._plate_b_guid)
        self._plate_a_interface = None
        self._plate_b_interface = None

    def flip_roles(self):
        self.plate_a, self.plate_b = self.plate_b, self.plate_a
        self._plate_a_guid, self._plate_b_guid = self._plate_b_guid, self._plate_a_guid
        self._plate_a_interface = None
        self._plate_b_interface = None
