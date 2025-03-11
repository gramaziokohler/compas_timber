import compas

if not compas.IPY:
    from typing import Generator  # noqa: F401
    from typing import List  # noqa: F401

from compas.geometry import Point
from compas_model.models import Model

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import Joint
from compas_timber.connections import JointTopology
from compas_timber.connections import WallJoint
from compas_timber.errors import BeamJoiningError


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
        return "TimberModel ({}) with {} elements(s) and {} joint(s).".format(str(self.guid), len(list(self.elements())), len(list(self.joints)))

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
        # type: () -> set[Joint]
        joints = set()  # some joints might apear on more than one interaction
        for interaction in self.interactions():
            if isinstance(interaction, Joint):
                joints.add(interaction)
        return joints

    @property
    def fasteners(self):
        # type: () -> Generator[Fastener, None, None]
        for element in self.elements():
            if getattr(element, "is_fastener", False):
                yield element

    @property
    def walls(self):
        # type: () -> Generator[Wall, None, None]
        for element in self.elements():
            if getattr(element, "is_wall", False):
                yield element

    @property
    def slabs(self):
        # type: () -> Generator[Slab, None, None]
        for element in self.elements():
            if getattr(element, "is_slab", False):
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
            vol = element.obb.volume  # TODO: include material density...? this uses volume as proxy for mass, which assumes all parts have equal density
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

    def add_element(self, element, parent=None, **kwargs):
        # resolve parent name to GroupNode object
        # TODO: upstream this to compas_model
        if parent and isinstance(parent, str):
            if not self.has_group(parent):
                raise ValueError("Group {} not found in model.".format(parent))
            parent = next((group for group in self._tree.groups if group.name == parent))
        return super(TimberModel, self).add_element(element, parent, **kwargs)

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

        element.name = group_name
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

    def _safely_get_interactions(self, node_pair):
        # type: (tuple) -> List[Interaction]
        try:
            return self._graph.edge_interactions(node_pair)
        except KeyError:
            return []

    def get_interactions_for_element(self, element):
        # type: (Element) -> List[Interaction]
        """Get all interactions for a given element.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The element to query.

        Returns
        -------
        list[:class:`~compas_model.interactions.Interaction`]
            A list of interactions for the given element.
        """

        negihbors = self._graph.neighbors(element.graph_node)
        result = []
        for nbr in negihbors:
            result.extend(self._safely_get_interactions((element.graph_node, nbr)))
            result.extend(self._safely_get_interactions((nbr, element.graph_node)))
        return result

    def add_joint(self, joint):
        # type: (Joint) -> None
        """Add a joint object to the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint`
            An instance of a Joint class.
        """
        self.add_elements(joint.generated_elements)
        for interaction in joint.interactions:
            element_a, element_b = interaction
            _ = self.add_interaction(element_a, element_b, joint)
            # TODO: should we create a bidirectional interaction here?

    def remove_joint(self, joint):
        # type: (Joint) -> None
        """Removes this joint object from the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        for interaction in joint.interactions:
            element_a, element_b = interaction
            self.remove_interaction(element_a, element_b)
        for element in joint.generated_elements:
            self.remove_element(element)

    def set_topologies(self, topologies):
        """TODO: calculate the topologies inside the model using the ConnectionSolver."""
        self._topologies = topologies

    def process_joinery(self, stop_on_first_error=False):
        """Process the joinery of the model. This methods checks the feasibility of the joints and instructs all joints to add their extensions and features.

        The sequence is important here since the feature parameters must be calculated based on the extended blanks.
        For this reason, the first iteration will only extend the beams, and the second iteration will add the features.

        Parameters
        ----------
        stop_on_first_error : bool, optional
            If True, the method will raise an exception on the first error it encounters. Default is False.

        Returns
        -------
        list[:class:`~compas_timber.errors.BeamJoiningError`]
            A list of errors that occurred during the joinery process.

        """
        errors = []
        joints = self.joints

        for joint in joints:
            try:
                joint.check_elements_compatibility()
                joint.add_extensions()
            except BeamJoiningError as bje:
                errors.append(bje)
                if stop_on_first_error:
                    raise bje

        for joint in joints:
            try:
                joint.add_features()
            except BeamJoiningError as bje:
                errors.append(bje)
                if stop_on_first_error:
                    raise bje
            # TODO: should we be handling the BTLxProcessing application errors differently?
            # TODO: Maybe a ProcessingApplicationError raised for the processing(s) that failed when adding the features to the elements?
            # TODO: This would allow us to catch the processing that failed with the necessary info, while applying the rest of the required by the joint processings that were sucessfull.  # noqa: E501
            except ValueError as ve:
                bje = BeamJoiningError(joint.elements, joint, debug_info=str(ve))
                errors.append(bje)
                if stop_on_first_error:
                    raise bje
        return errors

    def connect_adjacent_walls(self, max_distance=None):
        """Connects adjacent walls in the model.

        Parameters
        ----------
        max_distance : float, optional
            The maximum distance between walls to consider them adjacent. Default is 0.0.

        """
        self._clear_wall_joints()

        walls = list(self.walls)

        if not walls:
            return

        if max_distance is None:
            max_distance = max(wall.thickness for wall in walls)

        solver = ConnectionSolver()
        pairs = solver.find_intersecting_pairs(walls, rtree=True, max_distance=max_distance)
        for pair in pairs:
            wall_a, wall_b = pair
            result = solver.find_wall_wall_topology(wall_a, wall_b, tol=1e-6, max_distance=max_distance)

            topology = result[0]

            unsupported_topos = (JointTopology.TOPO_UNKNOWN, JointTopology.TOPO_I, JointTopology.TOPO_X)
            if topology in unsupported_topos:
                continue

            wall_a, wall_b = result[1], result[2]

            assert wall_a and wall_b

            # assume wall_a is the main, unless wall_b is explicitly marked as main
            # TODO: use the Rule system? this isn't good enough, a wall can totally be main and cross at the same time (in two different interactions)
            if wall_b.attributes.get("role", "cross") == "main":
                WallJoint.create(self, wall_b, wall_a, topology=topology)
            else:
                WallJoint.create(self, wall_a, wall_b, topology=topology)

    def _clear_wall_joints(self):
        for joint in self.joints:
            if isinstance(joint, WallJoint):
                self.remove_joint(joint)
