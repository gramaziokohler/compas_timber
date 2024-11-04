from compas_model.elements import Element
from compas_model.elements import reset_computed


class Fastener(Element):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    Parameters
    ----------
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    Attributes
    ----------
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    """




    def __init__(self, elements, **kwargs):
        super(Fastener, self).__init__(elements, **kwargs)
        self.elements = elements
        self.features = []
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
        return self._create_shape(self.frame, self.beams)

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
        raise NotImplementedError

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

    @staticmethod
    def _create_shape(frame, beams):
        # type: (Frame,  list[TimberElement]) -> Brep
        raise NotImplementedError

    # ==========================================================================
    # Featrues
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
            if not isinstance(features, list):
                features = [features]
            self.features = [f for f in self.features if f not in features]
