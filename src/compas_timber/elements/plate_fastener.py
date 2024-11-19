import math

from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Transformation
from compas.geometry import Vector

from compas_timber.elements.fastener import Fastener


class PlateFastener(Fastener):
    """
    A class to represent flat plate timber fasteners (e.g. steel plates).

    Parameters
    ----------
    shape : :class:`~compas.geometry.Geometry`
        The shape of the fastener at the XY plane origin.
    frame : :class:`~compas.geometry.Frame`
        The frame of the instance of the fastener that is applied to the model.
        The fastener should be defined at the XY plane origin with the x-axis pointing in the direction of the main_beam.
    holes : list of tuple, optional
        The holes of the fastener. Structure is as follows: [(point, diameter), ...]
    angle : float, optional (default=math.pi / 2)
        The angle of the fastener. The angle between the beam elements must be the same.

    Attributes
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    """

    def __init__(self, shape=None, frame=None, angle=math.pi / 2, **kwargs):
        super(PlateFastener, self).__init__(**kwargs)
        self._shape = shape
        self.frame = frame or Frame.worldXY()
        self.holes = []
        self.angle = angle
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
    def from_outline_thickness_holes_cutouts(
        cls, outline, angle=math.pi / 2, thickness=5, holes=None, cutouts=None, **kwargs
    ):
        """
        Constructs a fastener from an outline, cutouts and thickness.
        This should be constructed on the XY plane and oriented with the x-axis pointing in the direction of the main_beam.centerline.

        Parameters
        ----------
        outline : dict
            The outline of the fastener, given by :class:`~compas.geometry.NurbsCurve.__data__`.
        thickness : float, optional
            The thickness of the fastener.
        holes : tuple of list of tuple, optional
            The holes of the fastener. Structure is as follows:
            (beam_a_holes, beam_b_holes, ...) where beam_a_holes and beam_b_holes are lists of tuples of points and diameters.
        cutouts : list of :class:`~compas.geometry.NurbsCurve`, optional
            The cutouts of the fastener.

        Returns
        -------
        :class:`~compas_timber.elements.PlateFastener`

        """
        plate_fastener = cls(**kwargs)
        plate_fastener.outline = outline
        plate_fastener.angle = angle
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
        plate_fastener.name = data.get("name", None)
        plate_fastener.attributes = data.get("attributes", {})
        plate_fastener.outline = data.get("outline", None)
        plate_fastener.angle = data.get("angle", math.pi / 2)
        plate_fastener.thickness = data.get("thickness", 5)
        plate_fastener.holes = data.get("holes", [])
        plate_fastener.cutouts = data.get("cutouts", None)
        plate_fastener.frame = Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"])
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
        data["outline"] = self.outline
        data["angle"] = self.angle
        data["thickness"] = self.thickness
        data["holes"] = self.holes
        data["cutouts"] = self.cutouts
        data["frame"] = self.frame.__data__
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
            self._shape = Brep.from_extrusion(NurbsCurve.__from_data__(self.outline), vector)
            if self.cutouts:
                for cutout in self.cutouts:
                    curve = NurbsCurve.__from_data__(cutout)
                    cutout_brep = Brep.from_extrusion(curve, vector)
                    self._shape = self._shape - cutout_brep
            if self.holes:
                for list in self.holes:
                    for hole in list:
                        cylinder = Brep.from_cylinder(
                            Cylinder(
                                hole[1] * 0.5,
                                self.thickness * 2.0,
                                Frame(hole[0], Vector(1.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)),
                            )
                        )
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
