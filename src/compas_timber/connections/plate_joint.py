from abc import ABC
from abc import abstractmethod

from compas.geometry import dot_vectors

from compas_timber.errors import BeamJoiningError
from compas_timber.utils import get_polyline_segment_perpendicular_vector

from .joint import Joint
from .joint import JointTopology
from .solver import PlateConnectionSolver


class PlateJoint(Joint, ABC):
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
        self._reverse_a_planes = False
        self._reverse_b_planes = False

        self.plate_a_guid = str(self.plate_a.guid) if self.plate_a else kwargs.get("plate_a_guid", None)  # type: ignore
        self.plate_b_guid = str(self.plate_b.guid) if self.plate_b else kwargs.get("plate_b_guid", None)  # type: ignore

    def __repr__(self):
        return "PlateJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))

    @property
    def plates(self):
        return self.elements

    @property
    def elements(self):
        return self.plate_a, self.plate_b

    @property
    def a_planes(self):
        if self._reverse_a_planes:
            return (self.plate_a.planes[1], self.plate_a.planes[0])
        return (self.plate_a.planes[0], self.plate_a.planes[1])

    @property
    def b_planes(self):
        if self._reverse_b_planes:
            return (self.plate_b.planes[1], self.plate_b.planes[0])
        return (self.plate_b.planes[0], self.plate_b.planes[1])

    @property
    def a_outlines(self):
        if self._reverse_a_planes:
            return (self.plate_a.outlines[1], self.plate_a.outlines[0])
        return (self.plate_a.outlines[0], self.plate_a.outlines[1])

    @property
    def b_outlines(self):
        if self._reverse_b_planes:
            return (self.plate_b.outlines[1], self.plate_b.outlines[0])
        return (self.plate_b.outlines[0], self.plate_b.outlines[1])

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
        if reordered_elements and candidate.elements[0] != reordered_elements[0]:  # plates are in different order, reverse segment indices
            kwargs.update({"a_segment_index": candidate.b_segment_index, "b_segment_index": candidate.a_segment_index})  # pass reversed segment indices from candidate
        else:
            kwargs.update({"a_segment_index": candidate.a_segment_index, "b_segment_index": candidate.b_segment_index})  # pass segment indices from candidate
        return super(PlateJoint, cls).promote_joint_candidate(model, candidate, reordered_elements=reordered_elements, **kwargs)

    def add_extensions(self):
        """Adjusts plate outlines to outer shape required for the joint."""
        if self.plate_a and self.plate_b:
            if self.topology is None or (self.a_segment_index is None and self.b_segment_index is None):
                self.calculate_topology()
            self._reorder_planes_and_outlines()
            self._set_edge_planes()

    @abstractmethod
    def _set_edge_planes(self):
        """Sets the edge planes of the plates based on the joint topology."""
        raise NotImplementedError("This method should be implemented in subclasses.")

    def add_features(self):
        """Adds features to the plates based on the joint. this should be implemented in subclasses if needed."""
        pass

    def _reorder_planes_and_outlines(self):
        if dot_vectors(self.plate_b.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_a.outline_a, self.a_segment_index)) < 0:
            self._reverse_b_planes = True

        if self.topology == JointTopology.TOPO_EDGE_EDGE:
            if dot_vectors(self.plate_a.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_b.outline_a, self.b_segment_index)) < 0:
                self._reverse_a_planes = True

    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_plates_from_keys(*args, **kwargs)

    def restore_plates_from_keys(self, model):
        self.plate_a = model[self.plate_a_guid]
        self.plate_b = model[self.plate_b_guid]

    def flip_roles(self):
        self.plate_a, self.plate_b = self.plate_b, self.plate_a
        self.plate_a_guid, self.plate_b_guid = self.plate_b_guid, self.plate_a_guid
