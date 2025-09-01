from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import distance_line_line
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane

from compas_timber.errors import BeamJoiningError
from compas_timber.utils import get_polyline_segment_perpendicular_vector

from .joint import Joint
from .joint import JointTopology
from .solver import PlateConnectionSolver


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
        return Plane.from_frame(self.frame)

    @property
    def width(self):
        """Returns the width of the interface polyline."""
        return distance_line_line(self.polyline.lines[0], self.polyline.lines[2])


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
        data = super(PlateJoint, self).__data__
        data["plate_a_guid"] = self.plate_a_guid
        data["plate_b_guid"] = self.plate_b_guid
        data["topology"] = self.topology
        data["a_segment_index"] = self.a_segment_index
        data["b_segment_index"] = self.b_segment_index
        return data

    def __init__(self, plate_a=None, plate_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(PlateJoint, self).__init__(topology=topology, **kwargs)
        self.plate_a = plate_a
        self.plate_b = plate_b
        self.a_segment_index = a_segment_index
        self.b_segment_index = b_segment_index
        if self.plate_a and self.plate_b:
            if self.topology is None or (self.a_segment_index is None and self.b_segment_index is None):
                self.calculate_topology()
        self.a_outlines = None
        self.b_outlines = None
        self.a_planes = None
        self.b_planes = None

        self.plate_a_guid = kwargs.get("plate_a_guid", None) or str(self.plate_a.guid) if self.plate_a else None  # type: ignore
        self.plate_b_guid = kwargs.get("plate_b_guid", None) or str(self.plate_b.guid) if self.plate_b else None  # type: ignore

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
        return self.interface_a.polyline

    @property
    def interfaces(self):
        return self.interface_a, self.interface_b

    @property
    def interface_a(self):
        a_interface_polyline = Polyline(
            [
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index],
            ]
        )

        frame = Frame.from_points(a_interface_polyline.points[0], a_interface_polyline.points[1], a_interface_polyline.points[-2])
        if dot_vectors(frame.normal, Vector.from_start_end(self.b_planes[1].point, self.b_planes[0].point)) < 0:
            frame = Frame.from_points(a_interface_polyline.points[1], a_interface_polyline.points[0], a_interface_polyline.points[2])
        return PlateToPlateInterface(
            a_interface_polyline,
            frame,
            self.a_segment_index,
            self.topology,
        )

    @property
    def interface_b(self):
        b_interface_polyline = Polyline(
            [
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index],
            ]
        )
        frame = Frame.from_points(b_interface_polyline.points[0], b_interface_polyline.points[1], b_interface_polyline.points[-2])
        if dot_vectors(frame.normal, Vector.from_start_end(self.b_planes[0].point, self.b_planes[1].point)) < 0:
            frame = Frame.from_points(b_interface_polyline.points[1], b_interface_polyline.points[0], b_interface_polyline.points[2])
        return PlateToPlateInterface(
            b_interface_polyline,
            frame,
            self.b_segment_index,
            self.topology,
        )

    def calculate_topology(self, allow_reordering=False):
        """Calculate the topology of the joint based on the plates."""
        topo_results = PlateConnectionSolver().find_topology(self.plate_a, self.plate_b)
        if topo_results.topology == JointTopology.TOPO_UNKNOWN:
            raise ValueError("Could not determine topology for plates {0} and {1}.".format(self.plate_a, self.plate_b))
        if self.plate_a != topo_results.plate_a:
            if allow_reordering:
                self.plate_a, self.plate_b = topo_results.plate_a, topo_results.plate_b
            else:
                raise BeamJoiningError("The order of plates is incompatible with the joint topology. Try reversing the order of the plates.")
        self.topology = topo_results.topology
        self.a_segment_index = topo_results.a_segment_index
        self.b_segment_index = topo_results.b_segment_index
        return topo_results

    @classmethod
    def promote_joint_candidate(cls, model, candidate, reordered_elements=None, **kwargs):
        """Creates an instance of this joint from a generic joint.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this joint belong.
        candidate : :class:`~compas_timber.connections.Joint`
            The generic joint to be converted.
        reordered_elements : list(:class:`~compas_model.elements.Element`), optional
            The elements to be connected by this joint. If not provided, the elements of the generic joint will be used.
            This is used to explicitly define the element order.
        **kwargs : dict
            Additional keyword arguments that are passed to the joint's constructor.

        Returns
        -------
        :class:`compas_timber.connections.Joint`
            The instance of the created joint.

        """
        kwargs.update({"a_segment_index": candidate.a_segment_index, "b_segment_index": candidate.b_segment_index})  # pass segment indices from candidate
        return super(PlateJoint, cls).promote_joint_candidate(model, candidate, reordered_elements=reordered_elements, **kwargs)

    def add_features(self):
        """Add features to the plates based on the joint."""
        if self.plate_a and self.plate_b:
            if self.topology is None or (self.a_segment_index is None and self.b_segment_index is None):
                self.calculate_topology()
            self.reorder_planes_and_outlines()
            self._adjust_plate_outlines()
            self.plate_a.add_interface(self.interface_a)
            self.plate_b.add_interface(self.interface_b)

    def get_interface_for_plate(self, plate):
        if plate is self.plate_a:
            return self.interface_a
        elif plate is self.plate_b:
            return self.interface_b
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
        if self.topology == JointTopology.TOPO_EDGE_EDGE:
            if dot_vectors(self.plate_a.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_b.outline_a, self.b_segment_index)) < 0:
                self.a_planes = self.plate_a.planes[::-1]
                self.a_outlines = self.plate_a.outlines[::-1]

    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_plates_from_keys(*args, **kwargs)

    def restore_plates_from_keys(self, model):
        self.plate_a = model.element_by_guid(self.plate_a_guid)
        self.plate_b = model.element_by_guid(self.plate_b_guid)

    def flip_roles(self):
        self.plate_a, self.plate_b = self.plate_b, self.plate_a
        self.plate_a_guid, self.plate_b_guid = self.plate_b_guid, self.plate_a_guid


def move_polyline_segment_to_plane(polyline, segment_index, plane):
    """Move a segment of a polyline to the intersection with a plane."""
    start_pt = intersection_line_plane(polyline.lines[segment_index - 1], plane)
    if start_pt:
        polyline[segment_index] = start_pt
        if segment_index == 0:
            polyline[-1] = start_pt
    end_pt = intersection_line_plane(polyline.lines[(segment_index + 1) % len(polyline.lines)], plane)
    if end_pt:
        polyline[segment_index + 1] = end_pt
        if segment_index + 1 == len(polyline.lines):
            polyline[0] = end_pt
