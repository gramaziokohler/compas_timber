import math

from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
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
        self.frame = frame
        self._shape = shape
        self.angle = angle
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Plate Fastener(frame={!r}, name={})".format(self.frame, self.name)

    def __str__(self):
        # type: () -> str
        return "<Plate Fastener {} at frame={!r}>".format(self.name, self.frame)

    @classmethod
    def from_outline_thickness_interfaces_cutouts(
        cls, outline, angle=math.pi / 2, thickness=5, interfaces=None, cutouts=None, frame=None, **kwargs
    ):
        """
        Constructs a fastener from an outline, cutouts and thickness.
        This should be constructed on the XY plane and oriented with the x-axis pointing in the direction of the main_beam.centerline.

        Parameters
        ----------
        outline : list of :class:`~compas.geometry.Point`
            The outline of the fastener as a list of points.
        angle : float, optional
            The angle of the fastener. default is math.pi / 2
        thickness : float, optional
            The thickness of the fastener.
        interfaces : list of compas_timber.elements.FastenerTimberInterface, optional
            The connection interfaces to the timber elements
        cutouts : list of list of :class:`~compas.geometry.Point`, optional
            The cutouts of the fastener.
        frame : :class:`~compas.geometry.Frame`, optional
            The frame of the fastener, denoting its location in space.

        Returns
        -------
        :class:`~compas_timber.elements.PlateFastener`

        """
        plate_fastener = cls(**kwargs)
        plate_fastener.outline = outline
        plate_fastener.angle = angle
        plate_fastener.thickness = thickness
        plate_fastener.frame = frame
        for interface in interfaces:
            plate_fastener.add_interface(interface)
        plate_fastener.cutouts = cutouts
        return plate_fastener

    def add_interface(self, interface):
        """Add an interface to the fastener.

        Parameters
        ----------
        interface : :class:`~compas_timber.elements.FastenerTimberInterface`
            The interface to add.

        """
        interface.thickness = self.thickness
        interface.frame = self.frame
        interface.outline = None
        self.interfaces.append(interface)

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame
        for interface in self.interfaces:
            interface.frame = frame

    @property
    def holes(self):
        for interface in self.interfaces:
            for hole in interface.holes:
                yield hole

    @property
    def shapes(self):
        for interface in self.interfaces:
            for shape in interface.shapes:
                yield shape

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
                print("cutouts", self.cutouts)
                for cutout in self.cutouts:
                    cutout_brep = Brep.from_extrusion(cutout, vector)
                    self._shape -= cutout_brep
            if self.holes:
                for hole in self.holes:
                    cylinder = Brep.from_cylinder(
                        Cylinder(
                            hole["diameter"] * 0.5,
                            self.thickness * 2.0,
                            Frame(hole["point"], Vector(1.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)),
                        )
                    )
                    self._shape -= cylinder
            if self.shapes:
                for shape in self.shapes:
                    self._shape += shape
        return self._shape

    @property
    def geometry(self):
        """Constructs the geometry of the fastener as oriented in space.

        Returns
        -------
        :class:`~compas.geometry.Brep`

        """

        transformation = Transformation.from_frame(self.frame)
        return self.shape.transformed(transformation)
