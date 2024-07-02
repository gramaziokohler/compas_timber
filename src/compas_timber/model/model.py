from compas.geometry import Point
from compas_model.models import Model

from compas_timber.elements import Beam
from compas_timber.elements import Plate
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
        for element in model.elements():
            if isinstance(element, Beam):
                model._beams.append(element)
            elif isinstance(element, Plate):
                model._plates.append(element)
            elif isinstance(element, Wall):
                model._walls.append(element)
        for interaction in model.interactions():
            model._joints.append(interaction)
            interaction.restore_beams_from_keys(model)
            interaction.add_features()
        return model

    def __init__(self, *args, **kwargs):
        super(TimberModel, self).__init__()
        self._beams = []
        self._plates = []
        self._walls = []
        self._joints = []
        self._topologies = []  # added to avoid calculating multiple times

    def __str__(self):
        return "TimberModel ({}) with {} beam(s), {} plate(s) and {} joint(s).".format(
            self.guid, len(self.beams), len(self._plates), len(self.joints)
        )

    @property
    def beams(self):
        # type: () -> list[Beam]
        return self._beams

    @property
    def plates(self):
        # type: () -> list[Plate]
        return self._plates

    @property
    def joints(self):
        # type: () -> list[Joint]
        return self._joints

    @property
    def walls(self):
        # type: () -> list[Wall]
        return self._walls

    @property
    def topologies(self):
        return self._topologies

    @property
    def center_of_mass(self):
        # type: () -> Point
        total_vol = 0
        total_position = Point(0, 0, 0)

        for beam in self._beams:
            vol = beam.blank.volume
            point = beam.blank_frame.point
            point += beam.blank_frame.xaxis * (beam.blank_length / 2.0)
            total_vol += vol
            total_position += point * vol

        return Point(*total_position) * (1.0 / total_vol)

    @property
    def volume(self):
        # type: () -> float
        return sum([beam.blank.volume for beam in self._beams])  # TODO: add volume for plates

    def beam_by_guid(self, guid):
        # type: (str) -> Beam
        """Get a beam by its unique identifier.

        Parameters
        ----------
        guid : str
            The GUID of the beam to retrieve.

        Returns
        -------
        :class:`~compas_timber.elements.Beam`
            The beam with the specified GUID.

        """
        return self._guid_element[guid]

    def add_beam(self, beam):
        # type: (Beam) -> None
        """Adds a Beam to this model.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to add to the model.

        """
        _ = self.add_element(beam)
        self._beams.append(beam)

    def add_plate(self, plate):
        # type: (Beam) -> None
        """Adds a Beam to this model.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to add to the model.

        """
        _ = self.add_element(plate)
        self._plates.append(plate)

    def add_wall(self, wall):
        # type: (Wall) -> None
        """Adds a Wall to this model.

        Parameters
        ----------
        wall : :class:`~compas_timber.elements.Wall`
            The wall to add to the model.

        """
        _ = self.add_element(wall)
        self._walls.append(wall)

    def add_joint(self, joint, beams):
        # type: (Joint, tuple[Beam]) -> None
        """Add a joint object to the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint`
            An instance of a Joint class.

        beams : tuple(:class:`~compas_timber.elements.Beam`)
            The two beams that should be joined.

        """
        if len(beams) != 2:
            raise ValueError("Expected 2 parts. Got instead: {}".format(len(beams)))
        a, b = beams
        _ = self.add_interaction(a, b, interaction=joint)
        self._joints.append(joint)

    def remove_joint(self, joint):
        # type: (Joint) -> None
        """Removes this joint object from the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        a, b = joint.beams
        self.remove_interaction(a, b)
        self._joints.remove(joint)

    def set_topologies(self, topologies):
        """TODO: calculate the topologies inside the model using the ConnectionSolver."""
        self._topologies = topologies
