import math

from compas.datastructures import Part
from compas.geometry import Brep
from compas.geometry import Curve
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import add_vectors
from compas.geometry import subtract_vectors
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors


ANGLE_TOLERANCE = 1e-3  # [radians]
DEFAULT_TOLERANCE = 1e-6





class Plate(Part):
    """
    A class to represent timber plates (plywood sheeting, gypsum, etc.) with extrusions.

    Parameters
    ----------
    curves : :class:`~compas.geometry.Curve`
        The curve representing the boundary of the plate.
    thickness : float
        length of the extrusion, corresponding to the thickness of the plate

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        A local coordinate system of the plate:
        Origin is located on one cap face of the plate extrusion.
        x-axis arbitrary, can relate to assembly.
        y-axis arbitrary, can relate to assembly.
        z-axis direction of extrusion of the extrusion.
    length : float
        Length of the plate. NOT IMPLEMENTED YET could be length of blank.
    width : float
        Width of the plate. NOT IMPLEMENTED YET could be length of blank.
    height : float
        length of the extrusion, corresponding to the thickness of the plate
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this beam. NOT IMPLEMENTED YET
    faces : list(:class:`~compas.geometry.Frame`)
        A list of frames representing the 2 caps of the extrusion or two faces of the plate material.
        0: the frame of the part.
        1: offset frame of the part


    """

    def __init__(self, curves, thickness,  **kwargs):
        super(Plate, self).__init__()
        if not isinstance(curves, list):
            curves = [curves]
        self.curves = curves
        self.thickness = thickness
        self.features = []

    @property
    def __data__(self):
        data = {
            "curve": self.curve,
            "thickness": self.thickness,
            "key": self.key,
        }
        return data

    @classmethod
    def __from_data__(cls, data):
        instance = cls(data["curve"], data["thickness"])
        instance.key = data["key"]
        return instance



    @property
    def blank(self):
        raise NotImplementedError


    @property
    def faces(self):
        return [
            self.frame,
            Frame(
                Point(*add_vectors(self.frame.point, self.frame.normal * self.thickness)),
                self.frame.xaxis,
                self.frame.yaxis,
            )
        ]

    @property       #could be useful for self.blank / material stock
    def aabb(self):
        vertices, _ = self.blank.to_vertices_and_faces()
        x = [p.x for p in vertices]
        y = [p.y for p in vertices]
        z = [p.z for p in vertices]
        return min(x), min(y), min(z), max(x), max(y), max(z)


    @property
    def has_features(self):
        # TODO: move to compas_future... Part
        return len(self.features) > 0

    def __str__(self):
        return "Plate with thickness: {:.3f} and curve: {:.3f} ".format(
            self.thickness,
            self.curve,
        )

    @classmethod
    def from_curve(cls, curve, thickness, frame=None):
        """Define the beam from its centerline.

        Parameters
        ----------
        curve : :class:`~compas.geometry.Curve`
            The curve representing the boundary of the plate.
        thickness : float
            length of the extrusion, corresponding to the thickness of the plate

        Returns
        -------
        :class:`~compas_timber.parts.Plate`

        """
        if frame is None:
            frame = Frame(curve.curve_points[0], Vector.from_start_end(curve.curve_points[0], curve.curve_points[1]), Vector.from_start_end(curve.curve_points[0], curve.curve_points[-1]))

        return cls(curve, thickness, frame=frame)


    @property
    def curve_points(self):
        return self.curve.to_points()


    def add_features(self, features):
        """Adds one or more features to the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self.features.extend(features)

    def remove_features(self, features=None):
        """Removes a feature from the beam.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be removed. If None, all features will be removed.

        """
        if features is None:
            self.features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self.features = [f for f in self.features if f not in features]

