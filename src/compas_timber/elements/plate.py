from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Polygon
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import NurbsCurve
from compas.geometry import angle_vectors_signed
from compas.geometry import dot_vectors
from compas.datastructures import Mesh
from compas_model.elements import PlateElement
from compas.datastructures import Mesh
from compas_model.elements import PlateElement
from compas_model.elements import reset_computed
from compas.tolerance import Tolerance
from compas.itertools import pairwise

from compas.tolerance import Tolerance
from compas.itertools import pairwise


from .features import FeatureApplicationError


class Plate(PlateElement):

class Plate(PlateElement):

    """
    A class to represent timber plates (plywood, CLT, etc.) with uniform thickness.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`
        A local coordinate system of the plate:
        Origin is located at the starting point of the outline.


    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    shape : :class:`~compas.geometry.Brep`
        An extrusion representing the base geometry of this plate.
    outline : :class:`~compas.geometry.Polyline`
        A line representing the outline of this plate.
    thickness : float
        Thickness of the plate material.
    aabb : tuple(float, float, float, float, float, float)
        An axis-aligned bounding box of this plate as a 6 valued tuple of (xmin, ymin, zmin, xmax, ymax, zmax).


    """


    def __init__(self, bottom, top, features=None, frame=None, name=None, **kwargs):
        # type: (compas.geometry.Polygon, compas.geometry.Polygon, list[PlateFeature] | None, compas.geometry.Frame | None, str | None) -> None
        super(Plate, self).__init__(bottom, top)

        if not Polygon(bottom).is_planar:
            raise ValueError("The bottom outline points are not coplanar.")

        self._bottom = bottom
        self._top = top
        self._shape = None
        self.attributes = {}
        self._thickness = None
        self._frame = None
        self.features = features or []  # type: list[PlateFeature]
        self.attributes.update(kwargs)
        self.debug_info = []
        self.test = []
        self.test.append(Polygon(self._bottom))

    @property
    def frame(self):
        if self._frame is None:
            self._frame = Plate.get_frame_from_outline(self.outline)
        return self._frame

    @property
    def thickness(self):
        if self._thickness is None:
            bottom_frame = Frame.from_points(self.bottom.points[0], self.bottom.points[1], self.bottom.points[-2])
            top_frame = Frame.from_points(self.top.points[0], self.top.points[1], self.top.points[-2])
            self._thickness = bottom_frame.origin.distance_to_plane(Plane.from_frame(top_frame))
        return self._thickness


    @staticmethod
    def get_frame_from_outline(outline, vector = None):
        frame = Frame.from_points(outline.points[0], outline.points[1], outline.points[-2])
        aggregate_angle = 0.0   #this is used to determine if the outline is clockwise or counterclockwise
        for i in range(len(outline.points) - 1):
            first_vector = Vector.from_start_end(outline.points[i - 1], outline.points[i])
            second_vector = Vector.from_start_end(outline.points[i], outline.points[i + 1])
            aggregate_angle += angle_vectors_signed(first_vector, second_vector, frame.zaxis)
        if vector is not None and dot_vectors(frame.zaxis, vector) < 0:     # if the vector is pointing in the opposite direction from self.frame.normal
            if aggregate_angle > 0:
                frame = Frame(frame.point, frame.xaxis, -frame.yaxis)       # flips the frame if the frame.point is at an interior corner
            else:
                frame = Frame(frame.point, frame.yaxis, frame.xaxis)       # flips the frame if the frame.point is at an exterior corner
        return frame

    # @property
    # def shape(self):
    #     if not self._shape:
    #         self._shape = self.compute_shape()
    #     return self._shape


    def __repr__(self):
        # type: () -> str
        return "Plate(outline={!r}, thickness={}, )".format(self.outline, self.thickness)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def vector(self):
        return self.frame.zaxis * self.thickness

    @property
    def has_features(self):
        # TODO: move to compas_future... Part
        return len(self.features) > 0

    def __str__(self):
        return "Plate {} with thickness {:.3f} at {}".format(
        return "Plate {} with thickness {:.3f} at {}".format(
            self.outline,
            self.thickness,
            self.vector,
            self.frame,
        )

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_obb(self, inflate=0.0):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Parameters
        ----------
        inflate : float
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """
        vertices = [point for point in self._bottom]
        vertices.extend([point for point in self._top])
        for point in vertices:
            print(self.frame)
            point.transform(Transformation.from_change_of_basis(Frame.worldXY(), self.frame))
        obb = Box.from_points(vertices)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate

        obb.transform(Transformation.from_change_of_basis(self.frame, Frame.worldXY()))

        return obb


    # ==========================================================================
    # Alternative constructors
    # ==========================================================================


    @classmethod
    def from_outline_and_thickness(cls, outline, thickness, vector = None, **kwargs):
        # type: ( compas.geometry.Polyline, compas.geometry.Vector, dict) -> Plate
        """Create a plate element from an outline and vector. direction of extrusion is determined by the normal of the outline.

        Parameters
        ----------
        outline : :class:`compas.geometry.Polyline`
            The outline of the plate.
        thickness: float
            The thickness of the plate.
        vector : :class:`compas.geometry.Vector`
            The vector that determines direction of extrusion.

        Returns
        -------
        :class:`Plate`

        """

        bottom = Polygon(outline.points[0:-1])
        top = bottom.copy()
        frame = cls.get_frame_from_outline(outline, vector)
        top.translate(frame.normal * thickness)
        plate = Plate(bottom.points, top.points)

        plate._thickness = thickness
        plate._frame = frame
        return plate


    # ==========================================================================
    # Features
    # Features
    # ==========================================================================

    @reset_computed
    def add_features(self, features):
        """Adds one or more features to the plate.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self.features.extend(features)

    @reset_computed
    def remove_features(self, features=None):
        """Removes a feature from the plate.

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
