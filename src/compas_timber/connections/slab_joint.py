from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import distance_line_line
from compas.geometry import dot_vectors

from .joint import JointTopology
from .plate_joint import PlateJoint


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


class SlabConnectionInterface(object):
    """
    polyline : :class:`compas.geometry.Polyline`
        The outline of the interface area.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface area.
        xaxis : interface normal (towards other plate)
        yaxis : up along the interface side
        normal: width direction, perpendicular to the interface
    topology : literal(JointTopology)
        The topology of the joint in which the interface is used.
        E.g. L or T
    interface_role : literal(InterfaceRole)
        The role of the interface in the joint.

    """

    def __init__(self, polyline, frame, edge_index, topology, interface_role=None):
        self.polyline = polyline
        self.frame = frame
        self.edge_index = edge_index  # index of the edge in the plate outline where the interface is located
        self.topology = topology  # TODO: don't like this here
        self.interface_role = interface_role if interface_role else InterfaceRole.NONE

    # def __repr__(self):
    #     return "SlabConnectionInterface({0}, {1})".format(
    #         self.interface_role,
    #         JointTopology.get_name(self.topology),
    #     )

    def as_plane(self):
        """Returns the interface as a plane.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The plane of the interface.
        """
        return Plane.from_frame(self.frame)

    @property
    def width(self):
        """Returns the width of the interface polyline."""
        return distance_line_line(self.polyline.lines[0], self.polyline.lines[2])


class SlabJoint(PlateJoint):
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
    plate_a : :class:`compas_timber.elements.Plate`
        The first plate.
    plate_b : :class:`compas_timber.elements.Plate`
        The second plate.
    plates : tuple of :class:`compas_timber.elements.Plate`
        The plates that are connected.
    interface_a : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_a where it meets plate_b.
    interface_b : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_b where it meets plate_a.

    """

    @property
    def __data__(self):
        data = super(SlabJoint, self).__data__
        data["interfaces"] = self.interfaces
        return data

    def __init__(self, slab_a=None, slab_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(SlabJoint, self).__init__(slab_a, slab_b, topology, a_segment_index, b_segment_index, **kwargs)
        self.interface_a = None
        self.interface_b = None

    def __repr__(self):
        return "SlabJoint({0}, {1}, {2})".format(self.slab_a, self.slab_b, JointTopology.get_name(self.topology))

    @property
    def slabs(self):
        return self.elements

    @property
    def slab_a(self):
        return self.plate_a

    @property
    def slab_b(self):
        return self.plate_b

    @property
    def geometry(self):
        return self.interface_a.polyline

    @property
    def interfaces(self):
        return [self.interface_a, self.interface_b] if self.interface_a and self.interface_b else None

    def create_interfaces(self):
        a_interface_polyline = Polyline(
            [
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index],
            ]
        )
        frame_a = Frame.from_points(a_interface_polyline.points[0], a_interface_polyline.points[1], a_interface_polyline.points[-2])
        if dot_vectors(frame_a.normal, Vector.from_start_end(self.b_planes[1].point, self.b_planes[0].point)) < 0:
            frame_a = Frame.from_points(a_interface_polyline.points[1], a_interface_polyline.points[0], a_interface_polyline.points[2])
        interface_a = SlabConnectionInterface(
            a_interface_polyline,
            frame_a,
            self.a_segment_index,
            self.topology,
        )

        b_interface_polyline = Polyline(
            [
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index],
            ]
        )
        frame_b = Frame.from_points(b_interface_polyline.points[0], b_interface_polyline.points[1], b_interface_polyline.points[-2])
        if dot_vectors(frame_b.normal, Vector.from_start_end(self.b_planes[0].point, self.b_planes[1].point)) < 0:
            frame_b = Frame.from_points(b_interface_polyline.points[1], b_interface_polyline.points[0], b_interface_polyline.points[2])
        interface_b = SlabConnectionInterface(
            b_interface_polyline,
            frame_b,
            self.b_segment_index,
            self.topology,
        )
        return interface_a, interface_b

    def add_features(self):
        # NOTE: I called this add_features to fit with joint workflow, as interface is the slab equivalent of feature.
        """Add features to the plates based on the joint."""
        if self.interface_a and self.interface_b:
            self.slab_a.interfaces.remove(self.interface_a)
            self.slab_b.interfaces.remove(self.interface_b)
        self.interface_a, self.interface_b = self.create_interfaces()
        self.slab_a.interfaces.append(self.interface_a)
        self.slab_b.interfaces.append(self.interface_b)

    def get_interface_for_plate(self, plate):
        if plate is self.slab_a:
            return self.interface_a
        elif plate is self.slab_b:
            return self.interface_b
        else:
            raise ValueError("Plate not part of this joint.")
