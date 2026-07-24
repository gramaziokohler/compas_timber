from compas.data import Data
from compas.geometry import Point

from .joint import location_from_centerlines
from .solver import JointTopology

class JointCandidate(Data):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later grouped into a Clusters and then
    promoted to concrete joints.

    Please use `JointCandidate.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    topology : literal, one of :class:`JointTopology`, optional
        The topology by which the two elements interact. Defaults to `JointTopology.TOPO_UNKNOWN`.
    location : :class:`~compas.geometry.Point`, optional
        The estimated location of the interaction point of the two elements. If not provided, it is calculated
        from the elements' centerlines on first access.
    distance : float | None
        Distance between the elements.
    name : str, optional
        The name of the candidate.
    element_guids : tuple(str, str), optional
        GUIDs of the two elements, used during deserialization when the live elements aren't available yet.
    **kwargs : dict, optional
        Any additional attributes are set directly on the instance and survive serialization.

    Attributes
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    elements : tuple(:class:`~compas_model.elements.Element`)
        The elements joined by this candidate.
    interactions : list(tuple(:class:`~compas_model.elements.Element`, :class:`~compas_model.elements.Element`))
        The element pairs this candidate connects.
    generated_elements : list(:class:`~compas_model.elements.Element`)
        Always empty; a candidate never generates elements of its own.
    topology : literal, one of :class:`JointTopology`
        The topology by which the two elements interact.
    location : :class:`~compas.geometry.Point`
        The estimated location of the interaction point of the two elements.
    distance : float | None
        Distance between the elements.

    """

    def __init__(
        self,
        element_a=None,
        element_b=None,
        topology=None,
        location=None,
        distance=None,
        name=None,
        element_guids=None,
        **kwargs,
    ):
        super(JointCandidate, self).__init__(name=name)
        elements = tuple(e for e in (element_a, element_b) if e is not None)
        if elements:
            self._elements = elements
            self.element_guids = tuple(str(e.guid) for e in elements)
        elif element_guids:
            self._elements = ()
            self.element_guids = tuple(element_guids)
        else:
            raise ValueError("JointCandidate requires either elements or element_guids.")

        self.topology = topology
        self._location = location
        self.distance = distance 
        self._extra_kwargs = dict(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def __data__(self):
        data = {
            "name": self.name,
            "element_guids": self.element_guids,
            "topology": self.topology,
            "location": self._location,
            "distance": self.distance,
        }
        data.update(self._extra_kwargs)
        return data

    def __repr__(self):
        return "JointCandidate(element_a={}, element_b={}, topology={})".format(self.element_a, self.element_b, JointTopology.get_name(self.topology))

    @property
    def elements(self):
        return self._elements

    @property
    def element_a(self):
        return self._elements[0] if len(self._elements) > 0 else None

    @property
    def element_b(self):
        return self._elements[1] if len(self._elements) > 1 else None

    @property
    def interactions(self):
        return [(self.element_a, self.element_b)]
    @property
    def location(self):
        # all(()) == True, so we need to check len(self.elements) as well to avoid calculating location for joints without elements
        if self._location is None and all(self.elements) and len(self.elements) == 2:
            self._location = location_from_centerlines(self.elements)

        if self._location is None:
            raise ValueError("Location of the joint could not be determined. Please set it manually.")

        return self._location

    @location.setter
    def location(self, value):
        """Set the location of the joint."""
        if not isinstance(value, Point):
            raise TypeError("Location must be a Point.")
        self._location = value

    def reset_location(self):
        """Reset cached joint.location value to None so that it will be recalculated from the beam centerlines on next access."""
        self._location = None

    def restore_elements_from_keys(self, model):
        """Restores the reference to the elements associated with this candidate.

        This method is called by :class:`compas_timber.model.TimberModel` during de-serialization to restore the
        references.

        """
        self._elements = tuple(model[guid] for guid in self.element_guids)

    @classmethod
    def create(cls, model, *elements, **kwargs):
        """Creates an instance of this candidate and creates the new connection in `model`.

        Parameters
        ----------
        model : :class:`~compas_timber.model.TimberModel`
            The model to which the elements and this candidate belong.
        *elements : :class:`~compas_model.elements.Element`
            The elements to be connected by this candidate.
        **kwargs : dict
            Additional keyword arguments that are passed to the candidate's constructor.

        Returns
        -------
        :class:`compas_timber.connections.JointCandidate`
            The instance of the created candidate.

        """
        candidate = cls(*elements, **kwargs)
        model.add_joint_candidate(candidate)
        return candidate
    
class PlateJointCandidate(JointCandidate):
    """A PlateJointCandidate is an information-only joint for plate connections.

    It is used to create a first-pass joinery information which can be later used to create concrete joints.

    Parameters
    ----------
    plate_a : :class:`~compas_timber.elements.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.elements.Plate`
        Second plate to be joined.

    Attributes
    ----------
    plate_a : :class:`~compas_timber.elements.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.elements.Plate`
        Second plate to be joined.

    """

    def __init__(self, plate_a=None, plate_b=None, distance=None, **kwargs):
        # HACK: default distance to 0.0 (rather than None) to pass joint rules that expect a distance attribute,
        # matching the old `PlateJoint.__init__`'s behavior.
        super(PlateJointCandidate, self).__init__(element_a=plate_a, element_b=plate_b, distance=distance if distance is not None else 0.0, **kwargs)

    @property
    def plate_a(self):
        return self.element_a

    @property
    def plate_b(self):
        return self.element_b

    @property
    def location(self):
        if self._location is None:
            return Point(0,0,0) #Matches PlateJoint default TODO: actually calculate the location.

        return self._location

