from compas.geometry import Frame
from compas_model.elements import Element
from compas.geometry import NurbsCurve
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Vector
from compas.geometry import NurbsCurve
from compas.geometry import Transformation

class PlateFastener(Element):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    Parameters
    ----------
    shape : :class:`~compas.geometry.Geometry`
        The shape of the fastener at the XY plane origin.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    Attributes
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    """

    def __init__(self, shape=None, frame=None, **kwargs):
        super(PlateFastener, self).__init__(**kwargs)
        self._shape = shape
        self.frame = frame or Frame.worldXY()
        self.holes = []
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
        holes : tuple of list of tuple, optional
            The holes of the fastener. Structure is as follows:
            (beam_a_holes, beam_b_holes) where beam_a_holes and beam_b_holes are lists of tuples of points and diameters.
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

    @classmethod
    def __from_data__(cls, data):
        """Constructs a fastener from its data representation.

        Parameters
        ----------
        data : dict
            The data dictionary.

        Returns
        -------
        :class:`~compas_timber.elements.PlateFastener`

        """
        plate_fastener = cls()
        # plate_fastener._guid = data.get('guid', None)
        plate_fastener.name = data.get('name', None)
        plate_fastener.attributes = data.get('attributes', {})
        plate_fastener.outline = NurbsCurve.__from_data__(data['outline'])
        plate_fastener.thickness = data.get('thickness', 5)
        plate_fastener.holes = data.get('holes', [])
        plate_fastener.cutouts = [NurbsCurve.__from_data__(cutout) for cutout in data['cutouts']] if data.get('cutouts', None) else None
        plate_fastener.frame = Frame(data['frame']['point'], data['frame']['xaxis'], data['frame']['yaxis'])
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
    def __data__(self):
        data = super(PlateFastener, self).__data__
        # data['guid'] = self.guid
        data['outline'] = self.outline.__data__
        data['thickness'] = self.thickness
        data['holes'] = self.holes
        data['cutouts'] = [cutout.__data__ for cutout in self.cutouts] if self.cutouts else None
        data['frame'] = self.frame.__data__
        return data


    @property
    def shape(self):
        """Constructs the base shape of the fastener.This is located at the origin of the XY plane with the x-axis pointing in the direction of the main_beam.

        Returns
        -------
        :class:`~compas.geometry.Brep`

        """
        if not self._shape:
            vector = Vector(0, 0, self.thickness)
            self._shape = Brep.from_extrusion(self.outline, vector)
            if self.cutouts:
                for cutout in self.cutouts:
                    cutout_brep = Brep.from_extrusion(cutout, vector)
                    self._shape = self._shape - cutout_brep
            if self.holes:
                for list in self.holes:
                    for hole in list:
                        cylinder = Brep.from_cylinder(Cylinder(hole[1] * 0.5, self.thickness*2.0, Frame(hole[0], Vector(1.0,0.0,0.0), Vector(0.0,1.0,0.0))))
                        self._shape = self._shape - cylinder
        return self._shape


    @property
    def geometry(self):
        """Constructs the geometry of the fastener as oriented in space.

        Returns
        -------
        :class:`~compas.geometry.Brep`

        """
        if not self._geometry:
            self._geometry = self.shape.copy()
            transformation = Transformation.from_frame_to_frame(Frame.worldXY(), self.frame)
            self._geometry.transform(transformation)
        return self._geometry
