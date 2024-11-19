from compas.geometry import Frame
from compas_model.elements import Element


class Fastener(Element):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    Parameters
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    Attributes
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    """

    def __init__(self, geometry=None, frame=None, **kwargs):
        super(Fastener, self).__init__(**kwargs)
        self._geometry = geometry
        self.frame = frame or Frame.worldXY()
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Fastener(frame={!r}, name={})".format(self.frame, self.name)

    def __str__(self):
        # type: () -> str
        return "<Fastener {}>".format(self.name)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_fastener(self):
        return True

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node


class FastenerTimberInterface(object):

    def __init__(self, outline = None, thickness = None, holes = None):
        self.outline = outline
        self.thickness = thickness
        self.holes = holes

    def shape(self):
        """Return the shape of the interface between the fastener and the timber.
        this is represented by a Brep generated from an outline of the fastener geometry,
        the thickness of the fastener plate, and the locations and diameters of the fastener holes.
        """



    def __str__(self):
        return "FastenerTimberInterface"
