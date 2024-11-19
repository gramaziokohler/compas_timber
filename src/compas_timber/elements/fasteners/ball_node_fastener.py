from compas_model.elements import reset_computed
from compas_timber.utils import intersection_line_line_param
from compas.geometry import Sphere
from compas.geometry import Cylinder
from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Brep
from compas.geometry.intersections import intersection_sphere_line
from compas_timber.elements import DrillFeature
from compas_timber.elements import BrepSubtraction
from compas_timber.elements import CutFeature
from compas_timber.elements.fastener import Fastener


class BallNodeFastener(Fastener):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    Parameters
    ----------
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this fastener.
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    """

    @property
    def __data__(self):
        data = super(Fastener, self).__data__
        return data

    def __init__(self, geometry = None, **kwargs):
        super(BallNodeFastener, self).__init__(**kwargs)
        self.geometry = geometry
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        element_str = ["{} {}".format(element.__class__.__name__, element.key) for element in self.elements]
        return "Fastener({})".format(", ".join(element_str))

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_fastener(self):
        return True

    @property
    def shape(self):
        # type: () -> Brep
        return self.geometry

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    def __str__(self):
        return "Ball Node Fastener"

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, geometry):
        self._geometry = geometry

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.shape.to_mesh()
