from compas.geometry import Point
from compas_model.models import Model

from compas_timber.connections import Joint
from compas_timber.elements import Beam

# from compas_timber.elements import Plate
from compas_timber.elements import Wall


class TimberModel(Model):
    """Represents a timber model containing different elements such as walls, beams and joints.

    The timber model allows expressing the hierarchy and interactions between the different elements it contains.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.elements.Beam`)
        A list of beams assigned to this model.
    center_of_mass : :class:`~compas.geometry.Point`
        The calculated center of mass of the model.
    joints : list(:class:`~compas_timber.connections.Joint`)
        A list of joints assigned to this model.
    topologies :  list(dict)
        A list of JointTopology for model. dict is: {"detected_topo": detected_topo, "beam_a_key": beam_a_key, "beam_b_key":beam_b_key}
        See :class:`~compas_timber.connections.JointTopology`.
    volume : float
        The calculated total volume of the model.
    walls : list(:class:~compas_timber.elements.Wall)
        A list of walls assigned to this model.

    """

    @classmethod
    def __from_data__(cls, data):
        model = super(TimberModel, cls).__from_data__(data)
        for interaction in model.interactions():
            interaction.restore_beams_from_keys(model)
            interaction.add_features()
        return model

    def __init__(self, *args, **kwargs):
        super(TimberModel, self).__init__()
        self._topologies = []  # added to avoid calculating multiple times

    def __str__(self):
        return "TimberModel ({}) with {} beam(s) and {} joint(s).".format(
            self.guid, len(self.elements()), len(self.joints)
        )

    @property
    def beams(self):
        # type: () -> Generator[Beam]
        for element in self.elements():
            if isinstance(element, Beam):
                yield element

    # @property
    # def plates(self):
        # # type: () -> Generator[Plate]
        # for element in self.elements():
        #     if isinstance(element, Plate):
        #         yield element

    @property
    def joints(self):
        # type: () -> Generator[Joint]
        for interaction in self.interactions():
            if isinstance(interaction, Joint):
                yield interaction  # TODO: consider if there are other interaction types...

    @property
    def walls(self):
        # type: () -> Generator[Wall]
        for element in self.elements():
            if isinstance(element, Wall):
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
            vol = element.obb.volume        # TODO: include material density...? this uses volume as proxy for mass, which assumes all parts have equal density
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


    def add_joint(self, joint, elements):
        # type: (Joint, tuple[Element]) -> None
        """Add a joint object to the model.

        Parameters
        ----------
        interaction : :class:`~compas_timber.connections.Interaction`
            An instance of Interaction class.

        elements : tuple(:class:`~compas_timber.elements.Element`)
            The two elements that should be joined.

        """
        if len(elements) != 2:
            raise ValueError("Expected 2 parts. Got instead: {}".format(len(elements)))
        a, b = elements
        _ = super(TimberModel, self).add_interaction(a, b, interaction=joint)

    def remove_joint(self, joint):
        # type: (Joint) -> None
        """Removes this joint object from the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        a, b = joint.beams
        super(TimberModel, self).remove_interaction(a, b)

    def set_topologies(self, topologies):
        """TODO: calculate the topologies inside the model using the ConnectionSolver."""
        self._topologies = topologies
