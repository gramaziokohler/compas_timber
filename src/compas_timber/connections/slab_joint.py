from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_line

from .joint import JointTopology
from .plate_joint import PlateJoint
from .plate_joint import PlateToPlateInterface
from compas_timber.design.slab_details import LButtDetailB
from compas_timber.design.slab_details import TButtDetailB


class SlabToSlabInterface(PlateToPlateInterface):
    """Models a slab to slab interface.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline representing the outline of the interface.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface.
    edge_index : int
        The index of the edge in the polyline where the interface is located.
    topology : literal(JointTopology)
        The topology in which the slabs are connected.
    interface_role : literal(InterfaceRole), optional
        The role of the interface in the joint. Defaults to InterfaceRole.NONE.

    """

    def __init__(self, polyline, frame, edge_index, topology, interface_role=None, beams=None, detail_set=None):
        super(SlabToSlabInterface, self).__init__(polyline, frame, edge_index, topology, interface_role)
        self.beams = beams if beams else []
        self.detail_set = detail_set

    def __repr__(self):
        return "SlabToSlabInterface({0}, {1}, {2})".format(self.polyline, self.frame, JointTopology.get_name(self.topology))

    @property
    def beam_polyline(self):
        """Return the polyline bounding the centerlines of the interface beams."""
        if len(self.beams) > 1:
            points = []
            for base_line in [self.polyline.lines[1], self.polyline.lines[3]]:
                pts = []
                for beam in self.beams:
                    int_pt = Point(*intersection_line_line(beam.centerline, base_line)[1])
                    if int_pt:
                        pts.append(int_pt)
                if pts:
                    pts.sort(key=lambda pt: dot_vectors(pt - base_line.start, base_line.direction))
                    points.extend([pts[0], pts[-1]])
            return Polyline([points[0], points[1], points[2], points[3], points[0]])
        else:
            return self.polyline


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
        data["slab_a_guid"] = self._slab_a_guid
        data["slab_b_guid"] = self._slab_b_guid
        data["topology"] = self.topology
        data["a_segment_index"] = self.a_segment_index
        data["b_segment_index"] = self.b_segment_index
        return data

    def __init__(self, slab_a=None, slab_b=None, topology=None, a_segment_index=None, b_segment_index=None, detail_sets=None, **kwargs):
        super(SlabJoint, self).__init__(slab_a, slab_b, topology, a_segment_index, b_segment_index, **kwargs)

        self._slab_a_guid = kwargs.get("slab_a_guid", None) or str(self.slab_a.guid)  # type: ignore
        self._slab_b_guid = kwargs.get("slab_b_guid", None) or str(self.slab_b.guid)  # type: ignore
        self.detail_sets = detail_sets if detail_sets else {JointTopology.TOPO_L: LButtDetailB, JointTopology.TOPO_T: TButtDetailB}

    def __repr__(self):
        return "SlabJoint({0}, {1}, {2})".format(self.slab_a, self.slab_b, JointTopology.get_name(self.topology))

    @property
    def slab_a(self):
        """Return the first slab."""
        return self.plate_a

    @property
    def slab_b(self):
        """Return the second slab."""
        return self.plate_b

    @property
    def slabs(self):
        return self.elements

    @property
    def elements(self):
        return self.plate_a, self.plate_b

    @property
    def interfaces(self):
        """Return the interfaces of the slabs."""
        return [self.interface_a, self.interface_b]

    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_slabs_from_keys(*args, **kwargs)

    def restore_slabs_from_keys(self, model):
        self.plate_a = model.element_by_guid(self._slab_a_guid)
        self.plate_b = model.element_by_guid(self._slab_b_guid)
        self._calculate_interfaces()

    def flip_roles(self):
        self.plate_a, self.plate_b = self.plate_b, self.plate_a
        self._plate_a_guid, self._plate_b_guid = self._plate_b_guid, self._plate_a_guid
        self._calculate_interfaces()

    @property
    def interface_a(self):
        """Return the interface surface of slab_a where it meets slab_b."""
        interface = super(SlabJoint, self).interface_a
        return SlabToSlabInterface(
            polyline=interface.polyline,
            frame=interface.frame,
            edge_index=interface.edge_index,
            topology=self.topology,
            interface_role=interface.interface_role,
            detail_set=self.detail_sets.get(self.topology, None)
        )

    @property
    def interface_b(self):
        """Return the interface surface of slab_b where it meets slab_a."""
        interface = super(SlabJoint, self).interface_b
        return SlabToSlabInterface(
            polyline=interface.polyline,
            frame=interface.frame,
            edge_index=interface.edge_index,
            topology=self.topology,
            interface_role=interface.interface_role,
            detail_set=self.detail_sets.get(self.topology, None)
        )
