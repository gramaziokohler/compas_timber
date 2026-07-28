from abc import ABC
from abc import abstractmethod

from compas.geometry import Point
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
    location : :class:`compas.geometry.Point`, optional
        The location of the joint. If not provided, defaults to the origin.
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
        data["topology"] = self.topology
        data["a_segment_index"] = self.a_segment_index
        data["b_segment_index"] = self.b_segment_index
        return data

    def __init__(self, plate_a=None, plate_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(PlateJoint, self).__init__(elements=(plate_a, plate_b), topology=topology, **kwargs)
        self._a_segment_index = a_segment_index
        self._b_segment_index = b_segment_index
        self._reverse_a_planes = False
        self._reverse_b_planes = False
        self.distance = 0.0  # HACK: to pass joint rules that expect a distance attribute
        if self.plate_a and self.plate_b:
            if self.topology is None or (self.a_segment_index is None and self.b_segment_index is None):
                self.calculate_topology()

    def __repr__(self):
        return "PlateJoint({0}, {1}, {2})".format(self.plate_a, self.plate_b, JointTopology.get_name(self.topology))

    @property
    def plates(self):
        return self.elements

    @property
    def plate_a(self):
        return self.element_a

    @property
    def plate_b(self):
        return self.element_b

    @property
    def a_segment_index(self):
        if self.topology_data is not None:
            data = self.topology_data.data_for(self.plate_a)
            return data.edge_index if data else None
        return self._a_segment_index

    @a_segment_index.setter
    def a_segment_index(self, value):
        self._a_segment_index = value

    @property
    def b_segment_index(self):
        if self.topology_data is not None:
            data = self.topology_data.data_for(self.plate_b)
            return data.edge_index if data else None
        return self._b_segment_index

    @b_segment_index.setter
    def b_segment_index(self, value):
        self._b_segment_index = value

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

    @property
    def location(self):
        if self._location is None:
            self._location = Point(0, 0, 0)
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    def calculate_topology(self, allow_reordering=False):
        """Calculate the topology of the joint based on the plates."""
        topo_results = PlateConnectionSolver().find_topology(self.plate_a, self.plate_b)
        if topo_results.topology == JointTopology.TOPO_UNKNOWN:
            raise ValueError("Could not determine topology for plates {0} and {1}.".format(self.plate_a, self.plate_b))
        if topo_results.ordered_guids()[0] != str(self.plate_a.guid):
            if allow_reordering:
                self._elements = (self.plate_b, self.plate_a)
            else:
                raise BeamJoiningError(
                    beams=[self.plate_a, self.plate_b],
                    joint=self,
                    debug_info="The order of plates is incompatible with the joint topology. Try reversing the order of the plates.",
                )
        self.topology = topo_results.topology
        self.distance = topo_results.distance
        self._topology_data = topo_results
        if topo_results.location is not None:
            self.location = topo_results.location
        return topo_results

    # `promote_joint_candidate` is inherited from `Joint` unchanged: `a_segment_index`/`b_segment_index`
    # read through `topology_data` by element identity (see the properties above), so no manual
    # reversal-on-reorder is needed here regardless of how `reordered_elements` orders the plates.

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

    def clear_extensions(self):
        """Clears features from the plates based on the joint."""
        if self.a_segment_index is not None:
            self.element_a.remove_blank_extension(self.a_segment_index)
        if self.b_segment_index is not None:
            self.element_b.remove_blank_extension(self.b_segment_index)

    def _reorder_planes_and_outlines(self):
        if dot_vectors(self.plate_b.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_a.outline_a, self.a_segment_index)) < 0:
            self._reverse_b_planes = True

        if self.topology == JointTopology.TOPO_EDGE_EDGE:
            if dot_vectors(self.plate_a.frame.normal, get_polyline_segment_perpendicular_vector(self.plate_b.outline_a, self.b_segment_index)) < 0:
                self._reverse_a_planes = True
