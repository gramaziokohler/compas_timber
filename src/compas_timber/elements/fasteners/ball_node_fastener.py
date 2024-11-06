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
from compas_timber.elements.fasteners.fastener import Fastener



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
        self.features = []
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self.test = []

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
        element_str = ["{} {}".format(element.__class__.__name__, element.key) for element in self.elements]
        return "Fastener connecting {}".format(", ".join(element_str))

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_geometry(self):
        # type: (bool) -> compas.geometry.Brep
        """Compute the geometry of the fastener.

        Returns
        -------
        :class:`compas.geometry.Brep`

        """
        return self.shape

    def compute_aabb(self, inflate=0.0):
        # type: (float) -> compas.geometry.Box
        """Computes the Axis Aligned Bounding Box (AABB) of the element.

        Parameters
        ----------
        inflate : float, optional
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The AABB of the element.

        """
        raise NotImplementedError

    def compute_obb(self, inflate=0.0):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Parameters
        ----------
        inflate : float
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """
        raise NotImplementedError

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.shape.to_mesh()

    # ==========================================================================
    # Alternative constructors
    # ==========================================================================


    # ==========================================================================
    # Features
    # ==========================================================================

    @reset_computed
    def add_features(self, features):
        # type: (Feature | list[Feature]) -> None
        """Adds one or more features to the fastener.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self.features.extend(features)  # type: ignore

    @reset_computed
    def remove_features(self, features=None):
        # type: (None | Feature | list[Feature]) -> None
        """Removes a feature from the fastener.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be removed. If None, all features will be removed.

        """
        if features is None:
            self.features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self.features = [f for f in self.features if f not in features]
