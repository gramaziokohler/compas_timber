from functools import reduce
from operator import mul

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Transformation
from compas_model.elements import Element
from compas_model.elements import reset_computed
from compas_model.modifiers import Modifier


class ContainerElement(Element):
    """Base class for all container elements.

    This is an abstract class and should not be instantiated directly.

    Attributes
    ----------
    is_beam : bool
        True if the element is a beam.
    is_plate : bool
        True if the element is a plate.
    is_wall : bool
        True if the element is a wall.
    is_group_element : bool
        True if the element can be used as container for other elements.

    """

    @property
    def __data__(self):
        data = super(ContainerElement, self).__data__
        data["features"] = [f for f in self.features if not f.is_joinery]  # type: ignore
        return data

    def __init__(self, frame=None,elements=None, **kwargs):
        super(ContainerElement, self).__init__(**kwargs)
        self._transformation = Transformation.from_frame(frame) if frame else Frame.worldXY()
        self._elements = elements or []
        self._geometry = None
        self.debug_info = []


    @property
    def is_wall(self):
        return False

    @property
    def is_group_element(self):
        return True

    @property
    def elements(self):
        # type: () -> list[Element]
        """A list of elements contained within this container."""
        return self._elements


    @property
    def geometry(self):
        """The geometry of the element in the model's global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_modelgeometry()
        return self._geometry

    # ========================================================================
    # Geometry computation methods
    # ========================================================================

    def compute_modeltransformation(self):
        """Compute the transformation to model coordinates of this element
        based on its position in the spatial hierarchy of the model.
        # TODO: this is an override of the base class method. The difference is that it checks for self.model.
        # TODO: this is done in order to allow for an element to be handled without a model. Check if this is necessary.

        Returns
        -------
        :class:`compas.geometry.Transformation`

        """
        # type: () -> Transformation
        stack = []

        if self.transformation:
            stack.append(self.transformation)

        if self.model:
            parent = self.parent

            while parent:
                if parent.transformation:
                    stack.append(parent.transformation)
                parent = parent.parent

            if self.model.transformation:
                stack.append(self.model.transformation)

        if stack:
            return reduce(mul, stack[::-1])
        return Transformation()

    def compute_modelgeometry(self):
        """Compute the geometry of the element in model coordinates and taking into account the effect of interactions with connected elements.
        # TODO: this is an override of the base class method. The difference is that it checks for self.model.
        # TODO: this is done in order to allow for an element to be handled without a model. Check if this is necessary.

        Returns
        -------
        :class:`compas.geometry.Brep`

        """
        # type: () -> compas.geometry.Brep
        xform = self.modeltransformation
        modelgeometry = self.elementgeometry.transformed(xform)

        if self.model:
            for nbr in self.model.graph.neighbors_in(self.graphnode):
                modifiers: list[Modifier] = self.model.graph.edge_attribute((nbr, self.graphnode), name="modifiers")  # type: ignore
                if modifiers:
                    source = self.model.graph.node_element(nbr)
                    for modifier in modifiers:
                        modelgeometry = modifier.apply(source, modelgeometry)
        return modelgeometry

    # ========================================================================
    # Feature management & Modification methods
    # ========================================================================


    @reset_computed
    def add_element(self, element):
        # type: (Feature | list[Feature]) -> None
        """Adds an element to the container. The element being added should be located in reference to the container's frame.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        self._elements.append(element)  # add the element to this container
        if self.model:
            if element.model:
                element.model.remove_element(element)  # remove the element from its previous model.
            self.model.add_element(element, parent=self)  # add the element to this container's model.

    def remove_element(self, element):
        # type: (Feature) -> None
        """Removes an element from the container.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature`
            The feature to be removed.

        """
        self._elements.remove(element)
        if self.model:
            self.model.remove_element(element)  # remove the element from its model.
            self.model.add_element(element)  # add the element to the model without a parent aka at root. TODO: is this the desired behaviour? TODO: can/should I just set the treenode directly?

    def transformation_to_local(self):
        """Compute the transformation to local coordinates of this element
        based on its position in the spatial hierarchy of the model.

        Returns
        -------
        :class:`compas.geometry.Transformation`

        """
        # type: () -> Transformation
        return self.modeltransformation.inverse()

