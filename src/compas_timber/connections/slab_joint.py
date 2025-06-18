

from .joint import JointTopology
from .solver import PlateConnectionSolver
from .plate_joint import PlateJoint
from .plate_joint import PlateToPlateInterface


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

    def __init__(self, polyline, frame, edge_index, topology, interface_role=None, beams=None):
        super(SlabToSlabInterface, self).__init__(polyline, frame, edge_index, topology, interface_role)
        self.beams = beams if beams else []



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

    def __init__(self, slab_a=None, slab_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(SlabJoint, self).__init__(slab_a, slab_b,topology,a_segment_index,b_segment_index,**kwargs)

        self._slab_a_guid = kwargs.get("slab_a_guid", None) or str(self.slab_a.guid)  # type: ignore
        self._slab_b_guid = kwargs.get("slab_b_guid", None) or str(self.slab_b.guid)  # type: ignore

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
        print("slab.interfaces", self.interface_a, self.interface_b)  # DEBUG
        return [self.interface_a, self.interface_b]


    def add_features(self):
        super(SlabJoint, self).add_features()
        self.slab_a.add_interface(self.interface_a)
        self.slab_b.add_interface(self.interface_b)


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
        print("SlabJoint.interface_a")  # DEBUG
        interface = super(SlabJoint, self).interface_a
        return SlabToSlabInterface(
            polyline=interface.polyline,
            frame=interface.frame,
            edge_index=interface.edge_index,
            topology=self.topology,
            interface_role=interface.interface_role,
        )

    @property
    def interface_b(self):
        """Return the interface surface of slab_b where it meets slab_a."""
        print("SlabJoint.interface_b")  # DEBUG
        interface = super(SlabJoint, self).interface_b
        return SlabToSlabInterface(
            polyline=interface.polyline,
            frame=interface.frame,
            edge_index=interface.edge_index,
            topology=self.topology,
            interface_role=interface.interface_role,
        )


    def add_features(self):
        """Add features to the plates based on the joint."""
        if self.slab_a and self.slab_b:
            if self.topology is None or (self.a_segment_index is None and self.b_segment_index is None):
                topo_results = PlateConnectionSolver.find_plate_plate_topology(self.slab_a, self.slab_b)
                if not topo_results:
                    raise ValueError("Could not determine topology for plates {0} and {1}.".format(self.slab_a, self.slab_b))
                self.topology = topo_results[0]
                self.a_segment_index = topo_results[1][1]
                self.b_segment_index = topo_results[2][1]
            self.reorder_planes_and_outlines()
            self._adjust_plate_outlines()
            self.slab_a.add_interface(self.interface_a)
            self.slab_b.add_interface(self.interface_b)
