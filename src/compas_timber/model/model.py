import compas

if not compas.IPY:
    from typing import Generator  # noqa: F401

from compas.geometry import Point
from compas_model.models import Model

from compas_timber.connections import Joint


class TimberModel(Model):
    """Represents a timber model containing different elements such as walls, beams and joints.

    The timber model allows expressing the hierarchy and interactions between the different elements it contains.

    Attributes
    ----------
    beams : Generator[:class:`~compas_timber.elements.Beam`]
        A Generator object of all beams assigned to this model.
    plates : Generator[:class:`~compas_timber.elements.Plate`]
        A Generator object of all plates assigned to this model.
    joints : Generator[:class:`~compas_timber.connections.Joint`]
        A Generator object of all joints assigned to this model.
    walls : Generator[:class:`~compas_timber.elements.Wall`]
        A Generator object of all walls assigned to this model.
    center_of_mass : :class:`~compas.geometry.Point`
        The calculated center of mass of the model.
    topologies :  list(dict)
        A list of JointTopology for model. dict is: {"detected_topo": detected_topo, "beam_a_key": beam_a_key, "beam_b_key":beam_b_key}
        See :class:`~compas_timber.connections.JointTopology`.
    volume : float
        The calculated total volume of the model.

    """

    @classmethod
    def __from_data__(cls, data):
        model = super(TimberModel, cls).__from_data__(data)
        for interaction in model.interactions():
            interaction.restore_beams_from_keys(model)  # type: ignore
        return model

    def __init__(self, *args, **kwargs):
        super(TimberModel, self).__init__()
        self._topologies = []  # added to avoid calculating multiple times

    def __str__(self):
        # type: () -> str
        return "TimberModel ({}) with {} beam(s) and {} joint(s).".format(
            str(self.guid), len(list(self.elements())), len(list(self.joints))
        )

    @property
    def beams(self):
        # type: () -> Generator[Beam, None, None]
        # TODO: think about using `filter` instead of all these
        # TODO: add `is_beam`, `is_plate` etc. to avoid using `isinstance`
        for element in self.elements():
            if getattr(element, "is_beam", False):
                yield element

    @property
    def plates(self):
        # type: () -> Generator[Plate, None, None]
        for element in self.elements():
            if getattr(element, "is_plate", False):
                yield element

    @property
    def joints(self):
        # type: () -> List[Joint, None, None]
        joints = []
        for interaction in self.interactions():
            if isinstance(interaction, Joint):
                joints.append(interaction)
        return list(set(joints))  # remove duplicates

    @property
    def walls(self):
        # type: () -> Generator[Wall, None, None]
        for element in self.elements():
            if getattr(element, "is_wall", False):
                yield element

    @property
    def topologies(self):
        return self._topologies

    @property
    def center_of_mass(self):
        # type: () -> Point
        total_vol = 0
        total_position = Point(0, 0, 0)

        for element in self.elements():
            vol = (
                element.obb.volume
            )  # TODO: include material density...? this uses volume as proxy for mass, which assumes all parts have equal density
            point = element.obb.frame.point
            total_vol += vol
            total_position += point * vol

        return Point(*total_position) * (1.0 / total_vol)

    @property
    def volume(self):
        # type: () -> float
        return sum([element.obb.volume for element in self.elements()])

    def element_by_guid(self, guid):
        # type: (str) -> Beam
        """Get a beam by its unique identifier.

        Parameters
        ----------
        guid : str
            The GUID of the beam to retrieve.

        Returns
        -------
        :class:`~compas_model.elements.Element`
            The element with the specified GUID.

        """
        return self._guid_element[guid]

    def add_group_element(self, element, name=None):
        """Add an element which shall contain other elements.

        The container element is added to the group as well.

        TODO: upstream this to compas_model, maybe?

        Parameters
        ----------
        element : :class:`~compas_timber.elements.TimberElement`
            The element to add to the group.
        name : str, optional
            The name of the group to add the element to. If not provided, the element's name is used.

        Returns
        -------
        :class:`~compas_model.models.GroupNode`
            The group node containing the element.

        Raises
        ------
        ValueError
            If the group name is not provided and the element has no name.
            If a group with same name already exists in the model.

        Examples
        --------
        >>> from compas_timber.elements import Beam, Wall
        >>> from compas_timber.model import TimberModel
        >>> model = TimberModel()
        >>> wall1_group = model.add_group_element(Wall(5000, 200, 3000, name="wall1"))
        >>> beam_a = Beam(Frame.worldXY(), 100, 200, 300)
        >>> model.add_element(beam_a, parent=wall1_group)
        >>> model.has_group("wall1")
        True

        """
        # type: (TimberElement, str) -> GroupNode
        group_name = name or element.name

        if not element.is_group_element:
            raise ValueError("Element {} is not a group element.".format(element))

        if not group_name:
            raise ValueError("Group name must be provided or group element must have a name.")

        if self.has_group(group_name):
            raise ValueError("Group {} already exists in model.".format(group_name))

        group_node = self.add_group(group_name)
        self.add_element(element, parent=group_node)
        return group_node

    def has_group(self, group_name):
        # type: (str) -> bool
        """Check if a group with `group_name` exists in the model.

        TODO: upstream this to compas_model

        Parameters
        ----------
        group_name : str
            The name of the group to query.

        Returns
        -------
        bool
            True if the group exists in the model.
        """
        return group_name in (group.name for group in self._tree.groups)

    def get_elements_in_group(self, group_name, filter_=None):
        """Get all elements in a group with `group_name`.

        TODO: upstream this to compas_model

        Parameters
        ----------
        group_name : str
            The name of the group to query.
        filter_ : callable, optional
            A filter function to apply to the elements.

        Returns
        -------
        Generator[:class:`~compas_model.elements.Element`]
            A generator of elements in the group.

        """
        # type: (str, Optional[callable]) -> Generator[Element, None, None]
        if not self.has_group(group_name):
            raise ValueError("Group {} not found in model.".format(group_name))

        filter_ = filter_ or (lambda _: True)

        group = next((group for group in self._tree.groups if group.name == group_name))
        elements = (node.element for node in group.children)
        return filter(filter_, elements)

    def add_joint(self, joint):
        # type: (Joint) -> None
        """Add a joint object to the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint`
            An instance of a Joint class.
        """
        for interaction in joint.interactions:
            _ = self.add_interaction(*interaction)

    def remove_joint(self, joint):
        # type: (Joint) -> None
        """Removes this joint object from the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        a, b = joint.beams  # TODO: make this generic elements not beams
        super(TimberModel, self).remove_interaction(a, b)  # TODO: Can two elements share more than one interaction?

    def set_topologies(self, topologies):
        """TODO: calculate the topologies inside the model using the ConnectionSolver."""
        self._topologies = topologies

    def process_joinery(self):
        """Process the joinery of the model. This methods instructs all joints to add their extensions and features.

        The sequence is important here since the feature parameters must be calculated based on the extended blanks.
        For this reason, the first iteration will only extend the beams, and the second iteration will add the features.

        """
        for joint in self.joints:
            joint.add_extensions()

        for joint in self.joints:
            joint.add_features()
