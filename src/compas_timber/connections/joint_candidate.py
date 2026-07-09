from compas.geometry import Point

from .joint import Joint


class JointCandidate(Joint):
    """A JointCandidate is an information-only joint, which does not add any features to the elements it connects.

    It is used to create a first-pass joinery information which can be later grouped into a Clusters and then promoted to concrete joints.

    Please use `JointCandidate.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    distance : float | None
        Distance between the elements.
    ref_side_index_a : int | None
        Index of `element_a`'s matched long/main face, for `TOPO_FACE_FACE`. `None` otherwise.
    ref_side_index_b : int | None
        Index of `element_b`'s matched long/main face, for `TOPO_FACE_FACE`. `None` otherwise.

    Attributes
    ----------
    element_a : :class:`~compas_timber.elements.TimberElement`
        First element to be joined.
    element_b : :class:`~compas_timber.elements.TimberElement`
        Second element to be joined.
    distance : float | None
        Distance between the elements.
    ref_side_index_a : int | None
        Index of `element_a`'s matched long/main face.
    ref_side_index_b : int | None
        Index of `element_b`'s matched long/main face.

    """

    def __init__(self, element_a=None, element_b=None, distance=None, ref_side_index_a=None, ref_side_index_b=None, **kwargs):
        super(JointCandidate, self).__init__(elements=(element_a, element_b), **kwargs)
        # TODO: make distance a property of `Joint`?
        self.distance = distance if distance is not None else None
        self.ref_side_index_a = ref_side_index_a
        self.ref_side_index_b = ref_side_index_b

    def add_features(self):
        """This joint does not add any features."""
        pass


class PlateJointCandidate(JointCandidate):
    """A PlateJointCandidate is an information-only joint for plate connections.

    It is used to create a first-pass joinery information which can be later used to create concrete joints.

    Parameters
    ----------
    plate_a : :class:`~compas_timber.elements.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.elements.Plate`
        Second plate to be joined.
    a_segment_index : int | None
        Index of the outline segment in `plate_a` where the intersection occurs.
    b_segment_index : int | None
        Index of the outline segment in `plate_b` where the intersection occurs.

    Attributes
    ----------
    plate_a : :class:`~compas_timber.elements.Plate`
        First plate to be joined.
    plate_b : :class:`~compas_timber.elements.Plate`
        Second plate to be joined.
    a_segment_index : int | None
        Index of the outline segment in `plate_a` where the intersection occurs.
    b_segment_index : int | None
        Index of the outline segment in `plate_b` where the intersection occurs.
    ref_side_index_a : int | None
        Index of `plate_a`'s matched main face, for `TOPO_FACE_FACE`. `None` otherwise.
    ref_side_index_b : int | None
        Index of `plate_b`'s matched main face, for `TOPO_FACE_FACE`/`TOPO_EDGE_FACE`. `None` otherwise.

    """

    def __init__(self, plate_a=None, plate_b=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(PlateJointCandidate, self).__init__(element_a=plate_a, element_b=plate_b, **kwargs)
        self.a_segment_index = a_segment_index
        self.b_segment_index = b_segment_index

    @property
    def plate_a(self):
        return self.element_a

    @property
    def plate_b(self):
        return self.element_b

    @property
    def location(self):
        # plates have no `.centerline`, so unlike the base `Joint.location`, this can't fall back to
        # a centerline-based computation — default to the origin instead.
        if self._location is None:
            self._location = Point(0, 0, 0)
        return self._location

    @location.setter
    def location(self, value):
        self._location = value


class BeamPlateJointCandidate(JointCandidate):
    """A BeamPlateJointCandidate is an information-only joint for beam-to-plate/panel connections.

    It is used to create a first-pass joinery information which can be later used to create concrete joints.

    Parameters
    ----------
    beam : :class:`~compas_timber.elements.Beam`
        The beam to be joined.
    plate : :class:`~compas_timber.elements.Plate` or :class:`~compas_timber.elements.Panel`
        The plate or panel to be joined.
    segment_index : int | None
        Index of the outline segment involved in the intersection, for edge-related topologies
        (`TOPO_END_EDGE`, `TOPO_MIDDLE_EDGE`, `TOPO_ALONG_EDGE`). `None` otherwise.
    beam_ref_side_index : int | None
        Index of the beam's matched long face, for `TOPO_FACE_FACE`. `None` otherwise.
    plate_ref_side_index : int | None
        Index of the plate's matched main face, for `TOPO_FACE_FACE`/`TOPO_END_FACE`. `None` otherwise.

    Attributes
    ----------
    beam : :class:`~compas_timber.elements.Beam`
        The beam involved in the connection.
    plate : :class:`~compas_timber.elements.Plate` or :class:`~compas_timber.elements.Panel`
        The plate or panel involved in the connection.
    segment_index : int | None
        Index of the outline segment involved in the intersection.
    beam_ref_side_index : int | None
        Index of the beam's matched long face.
    plate_ref_side_index : int | None
        Index of the plate's matched main face.

    """

    def __init__(self, beam=None, plate=None, segment_index=None, beam_ref_side_index=None, plate_ref_side_index=None, **kwargs):
        super(BeamPlateJointCandidate, self).__init__(element_a=beam, element_b=plate, **kwargs)
        self.segment_index = segment_index
        self.beam_ref_side_index = beam_ref_side_index
        self.plate_ref_side_index = plate_ref_side_index

    @property
    def beam(self):
        return self.element_a

    @property
    def plate(self):
        return self.element_b
