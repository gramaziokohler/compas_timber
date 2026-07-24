from compas.data import Data


class TopologyData(Data):
    """Base class holding per-element topology data for a single element within a `JointCandidate`/`SolverResult`.

    Parameters
    ----------
    element : :class:`~compas_model.elements.Element`
        The element this data describes.
    location : :class:`~compas.geometry.Point`, optional
        The point on this element closest to the joint.

    Attributes
    ----------
    element : :class:`~compas_model.elements.Element`
        The element this data describes.
    location : :class:`~compas.geometry.Point`
        The point on this element closest to the joint.

    """

    def __init__(self, element=None, location=None):
        super(TopologyData, self).__init__()
        self.element = element
        self.location = location

    @property
    def __data__(self):
        return {"element": self.element, "location": self.location}


class BeamTopologyData(TopologyData):
    """Per-beam topology data describing how a single beam participates in a connection.

    Parameters
    ----------
    beam : :class:`~compas_timber.elements.Beam`
        The beam this data describes.
    role : literal("end", "through"), optional
        ``"end"`` if this beam meets the other beam at one of its own ends, ``"through"`` if it
        meets it along its length (mid-span). ``None`` when the topology is unknown.
    end : literal("start", "end"), optional
        Which end of this beam is involved in the connection. ``None`` when `role` is ``"through"``.
    ref_side_index : int, optional
        Index of this beam's reference side that faces the other beam. ``None`` when not
        applicable (e.g. parallel beams, unknown topology).
    location : :class:`~compas.geometry.Point`, optional
        The point on this beam's centerline closest to the joint.

    Attributes
    ----------
    beam : :class:`~compas_timber.elements.Beam`
        Alias of `element`.
    role : literal("end", "through") or None
    end : literal("start", "end") or None
    ref_side_index : int or None
    location : :class:`~compas.geometry.Point`

    """

    def __init__(self, beam=None, role=None, end=None, ref_side_index=None, location=None):
        super(BeamTopologyData, self).__init__(element=beam, location=location)
        self.role = role
        self.end = end
        self.ref_side_index = ref_side_index

    @property
    def __data__(self):
        data = super(BeamTopologyData, self).__data__
        data["beam"] = data.pop("element")
        data["role"] = self.role
        data["end"] = self.end
        data["ref_side_index"] = self.ref_side_index
        return data

    @property
    def beam(self):
        return self.element

    @beam.setter
    def beam(self, value):
        self.element = value

    def __repr__(self):
        return "BeamTopologyData(beam={}, role={}, end={}, ref_side_index={})".format(
            self.beam.name if self.beam else None, self.role, self.end, self.ref_side_index
        )


class PlateTopologyData(TopologyData):
    """Per-plate topology data describing how a single plate participates in a connection.

    Parameters
    ----------
    plate : :class:`~compas_timber.elements.Plate`
        The plate this data describes.
    role : literal("edge", "face"), optional
        ``"edge"`` if this plate's edge participates in the connection, ``"face"`` if this plate is
        the face-only side of a `TOPO_EDGE_FACE` connection. ``None`` when the topology is unknown.
    edge_index : int, optional
        The index of the segment in this plate's outline where the connection occurs. ``None`` when
        `role` is ``"face"`` or the topology is unknown.
    location : :class:`~compas.geometry.Point`, optional
        The point on this plate closest to the joint.

    Attributes
    ----------
    plate : :class:`~compas_timber.elements.Plate`
        Alias of `element`.
    role : literal("edge", "face") or None
    edge_index : int or None
    location : :class:`~compas.geometry.Point`

    """

    def __init__(self, plate=None, role=None, edge_index=None, location=None):
        super(PlateTopologyData, self).__init__(element=plate, location=location)
        self.role = role
        self.edge_index = edge_index

    @property
    def __data__(self):
        data = super(PlateTopologyData, self).__data__
        data["plate"] = data.pop("element")
        data["role"] = self.role
        data["edge_index"] = self.edge_index
        return data

    @property
    def plate(self):
        return self.element

    @plate.setter
    def plate(self, value):
        self.element = value

    def __repr__(self):
        return "PlateTopologyData(plate={}, role={}, edge_index={})".format(self.plate.name if self.plate else None, self.role, self.edge_index)
