from compas.geometry import Frame
from compas_model.elements import Element
from compas.geometry import NurbsCurve
from compas.geometry import Brep
from compas.geometry import Cylinder

class PlateFastener(Element):
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
        super(PlateFastener, self).__init__(**kwargs)
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


    # ==========================================================================
    # Class methods
    # ==========================================================================

    @classmethod
    def from_outline_thickness_holes_cutouts(cls, outline,  thickness = 5, holes = None, cutouts = None, **kwargs):
        """Constructs a fastener from an outline, cutouts and thickness.

        Parameters
        ----------
        outline : :class:`~compas.geometry.NurbsCurve`
            The outline of the fastener.
        thickness : float, optional
            The thickness of the fastener.
        holes : list of tuple, optional
            The holes of the fastener. Each tuple contains a point and a diameter.
        cutouts : list of :class:`~compas.geometry.NurbsCurve`, optional
            The cutouts of the fastener.

        Returns
        -------
        :class:`~compas_timber.elements.PlateFastener`

        """
        plate_fastener = cls(**kwargs)
        plate_fastener.outline = outline
        plate_fastener.thickness = thickness
        plate_fastener.holes = holes
        plate_fastener.cutouts = cutouts

        return plate_fastener

    # ==========================================================================
    # Methods
    # ==========================================================================

    def add_hole(self, point, diameter):
        """Adds a hole to the fastener.

        Parameters
        ----------
        point : :class:`~compas.geometry.Point`
            The point of the hole.
        diameter : float
            The diameter of the hole.

        """
        self.holes.append((point, diameter))

    @property
    def geometry(self):
        """Constructs the geometry of the fastener.

        Returns
        -------
        :class:`~compas.geometry.Geometry`

        """
        if not self._geometry:
            self._geometry = Brep.from_extrusion(self.outline, self.thickness)
            for cutout in self.cutouts:
                cutout_brep = Brep.from_extrusion(cutout, self.thickness)
                self._geometry = self._geometry - cutout_brep
            for hole in self.holes:
                cylinder = Brep.from_cylinder(Cylinder(hole[1] * 0.5, self.thickness, Frame(hole[0], Vector.worldX, Vector.worldY)))
                self._geometry = self._geometry - cylinder
        return self._geometry
