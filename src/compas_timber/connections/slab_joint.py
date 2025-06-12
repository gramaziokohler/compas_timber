from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import dot_vectors

from compas_timber.utils import get_polyline_segment_perpendicular_vector

from .plate_joint import PlateJoint
from .joint import JointTopology
from .solver import ConnectionSolver


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
    plate_a_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_a where it meets plate_b.
    plate_b_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_b where it meets plate_a.

    """

    @property
    def __data__(self):
        data = super(PlateJoint, self).__data__
        data["slab_a_guid"] = self._slab_a_guid
        data["slab_b_guid"] = self._slab_b_guid
        data["topology"] = self.topology
        data["a_segment_index"] = self.a_segment_index
        data["b_segment_index"] = self.b_segment_index
        return data

    def __init__(self, slab_a=None, slab_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(PlateJoint, self).__init__(slab_a, slab_b,topology,a_segment_index,b_segment_index,**kwargs)

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


    def add_features(self):
        super(SlabJoint, self).add_features()
        self.add_elements()


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
