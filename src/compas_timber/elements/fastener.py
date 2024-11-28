from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import NurbsCurve
from compas.geometry import Transformation
from compas.geometry import Vector

from compas_timber.elements.features import DrillFeature
from compas_timber.elements.timber import TimberElement
from compas_timber.utils import intersection_line_box


class Fastener(TimberElement):
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

    def __init__(self, shape=None, frame=None, **kwargs):
        super(Fastener, self).__init__(**kwargs)
        self._shape = shape
        self.interfaces = []
        self.frame = frame
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Fastener(frame={!r}, name={})".format(self.frame, self.name)

    def __str__(self):
        # type: () -> str
        return "<Fastener {}>".format(self.name)

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame

    @property
    def is_fastener(self):
        return True

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    def copy(self):
        cls = type(self)
        fast = cls(shape=self._shape, frame=self.frame)
        fast.interfaces = [interface.copy() for interface in self.interfaces]
        fast.debug_info = self.debug_info
        return fast

    @property
    def geometry(self):
        """returns the geometry of the fastener in the model"""
        return self.shape.transformed(Transformation.from_frame(self.frame))


class FastenerTimberInterface(object):
    """A class to represent the interface between a fastener and a timber element.

    Parameters
    ----------
    outline : :class:`~compas.geometry.Geometry`
        The outline of the fastener geometry.
    thickness : float
        The thickness of the fastener plate.
    holes : list of dict, optional
        The holes of the fastener. Structure is as follows:
        {
        "point": compas.geometry.Point,
        "diameter": float,
        "vector": compas.geometry.Vector, optional, if none, the hole is assumed to be perpendicular to the frame
        "through": bool, optional, if True, the hole goes through the timber element
        }
    frame : :class:`~compas.geometry.Frame`
        The frame of the instance of the fastener that is applied to the model.
    shapes : :class:`~compas.geometry.Geometry`
        Input for extra geometric elements. These should be solids that can be booleaned with the fastener geometry.
    feature_defs : list of compas_timber.Feature
        A list of user defined features that are applied to the timber element.

    Attributes
    ----------
    outline : :class:`~compas.geometry.Geometry`
        The outline of the fastener geometry.
    thickness : float
        The thickness of the fastener plate.
    holes : list of dict, optional
        The holes of the fastener. Structure is as follows:
        {
        "point": compas.geometry.Point,
        "diameter": float,
        "vector": compas.geometry.Vector, optional, if none, the hole is assumed to be perpendicular to the frame
        "through": bool, optional, if True, the hole goes through the timber element
        }
    frame : :class:`~compas.geometry.Frame`
        The frame of the instance of the fastener that is applied to the model.
    features : list of :class:`~compas_timber.parts.Feature`
        The features that are applied by this interface to the timber element. This returns the features in world coordinates.


    """

    def __init__(self, outline_pts=None, thickness=None, holes=None, frame=Frame.worldXY(), shapes=None, features=None):
        self.outline_pts = outline_pts
        self.thickness = thickness
        self.holes = holes
        self.frame = frame
        self.shapes = shapes
        self.features = features
        self.element = None
        self.fastener = None
        self._shape = None
        self.test = []

    def __str__(self):
        return "FastenerTimberInterface at {}".format(self.frame)

    @property
    def __data__(self):
        return {
            "outline_pts": self.outline_pts.__data__,
            "thickness": self.thickness,
            "holes": self.holes.__data__,
            "frame": self.frame.__data__,
            "shapes": self.shapes,
            "feature_defs": self.feature_defs,
        }

    @property
    def plate(self):
        """Generate a plate from outline, thickness, and holes."""
        if not self.outline_pts:
            return None
        plate = Brep.from_extrusion(
            NurbsCurve.from_points(self.outline_pts, degree=1), Vector(0.0, 0.0, 1.0) * self.thickness
        )
        for hole in self.holes:
            frame = Frame(hole["point"], self.frame.xaxis, self.frame.yaxis)
            hole = Brep.from_cylinder(Cylinder(hole["diameter"] / 2, self.thickness * 2, frame))
            plate -= hole
        return plate

    @property
    def shape(self):
        """Return a Brep representation of the interface located at the WorldXY origin."""
        if not self._shape:
            if self.plate:
                self._shape = self.plate
                if self.shapes:
                    for shape in self.shapes:
                        self._shape += shape
            elif self.shapes:
                self._shape = self.shapes[0]
                for shape in self.shapes[1:]:
                    self._shape += shape
        return self._shape

    @property
    def geometry(self):
        """returns the geometry of the interface in the model (oriented on the timber element)"""
        return self.shape.transformed(Transformation.from_frame(self.frame))

    def add_features(self):
        """Add a feature to the interface."""
        features = []
        for hole in self.holes:
            features.append(self.get_hole_feature(hole))
            print("hole", hole)
        for feature in self.features:
            feature = feature.copy()
            feature.transform(Transformation.from_frame(self.frame))
            features.append(feature)
        for feature in features:
            self.element.add_feature(feature)

    def get_hole_feature(self, hole):
        """Get the line that goes through the timber element."""
        vector = hole["vector"] or Vector(0.0, 0.0, 1.0)
        length = vector.length
        point = hole["point"] - vector * length * 0.5
        drill_line = Line.from_point_direction_length(point, vector, length)
        drill_line.transform(Transformation.from_frame(self.frame))
        if hole["through"]:
            pts = intersection_line_box(drill_line, self.element.blank)
            if pts:
                drill_line = Line(*pts)
                length = drill_line.length
        return DrillFeature(drill_line, hole["diameter"], length)

    def copy(self):
        fast = FastenerTimberInterface(
            self.outline_pts, self.thickness, self.holes, shapes=self.shapes, features=self.features
        )
        fast._shape = self._shape
        fast.element = self.element
        fast.fastener = self.fastener
        return fast
