import math

from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Brep
from compas.geometry import add_vectors
from compas.geometry import dot_vectors
from compas.geometry import bounding_box
from compas.tolerance import TOL
from compas_model.elements import Element
from compas_model.elements import reset_computed


from .features import FeatureApplicationError


class Plate(Element):
    """
    A class to represent timber beams (studs, slats, etc.) with rectangular cross-sections.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`
        A local coordinate system of the beam:
        Origin is located at the starting point of the centerline.
        x-axis corresponds to the centerline (major axis), usually also the fibre direction in solid wood beams.
        y-axis corresponds to the width of the cross-section, usually the smaller dimension.
        z-axis corresponds to the height of the cross-section, usually the larger dimension.
    length : float
        Length of the beam
    width : float
        Width of the cross-section
    height : float
        Height of the cross-section

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this beam.
    length : float
        Length of the beam.
    width : float
        Width of the cross-section
    height : float
        Height of the cross-section
    shape : :class:`~compas.geometry.Box`
        A feature-less box representing the parametric geometry of this beam.
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this beam.
    faces : list(:class:`~compas.geometry.Frame`)
        A list of frames representing the 6 faces of this beam.
        0: +y (side's frame normal is equal to the beam's Y positive direction)
        1: +z
        2: -y
        3: -z
        4: -x (side at the starting end)
        5: +x (side at the end of the beam)
    centerline : :class:`~compas.geometry.Line`
        A line representing the centerline of this beam.
    centerline_start : :class:`~compas.geometry.Point`
        The point at the start of the centerline of this beam.
    centerline_end : :class:`~compas.geometry.Point`
        The point at the end of the centerline of this beam.
    aabb : tuple(float, float, float, float, float, float)
        An axis-aligned bounding box of this beam as a 6 valued tuple of (xmin, ymin, zmin, xmax, ymax, zmax).
    long_edges : list(:class:`~compas.geometry.Line`)
        A list containing the 4 lines along the long axis of this beam.
    midpoint : :class:`~compas.geometry.Point`
        The point at the middle of the centerline of this beam.

    """

    @property
    def __data__(self):
        data = super(Plate, self).__data__
        data["thickness"] = self.thickness
        return data

    def __init__(self, outline, thickness, vector, **kwargs):
        super(Plate, self).__init__(**kwargs)
        if not outline.is_closed:
            raise ValueError("The outline points are not coplanar.")
        self.outline = outline
        self.thickness = thickness
        self.features = []
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        face = Brep.from_curves([outline])
        face = face.brep_faces[0]
        if vector is not None:
            if dot_vectors(face.normal, vector) > 0:
                print("reversing")
                outline.reverse()
        self.frame = Frame(outline.points[0], outline.points[1]-outline.points[0], face.normal)
        self.vector = self.frame.zaxis * self.thickness

        for point in outline.points:
            if point.distance_to_plane(Plane.from_frame(self.frame)) > 0.001:
                raise ValueError("The outline points are not coplanar.")


    def __repr__(self):
        # type: () -> str
        return "Plate(outline={!r}, thickness={}, )".format(self.outline, self.thickness)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def shape(self):
        return self._create_shape(self.outline, self.vector)

    @property
    def has_features(self):
        # TODO: move to compas_future... Part
        return len(self.features) > 0

    def __str__(self):
        return "Plate {:.3f} x {:.3f} at {}".format(
            self.outline,
            self.thickness,
            self.frame,
        )

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_geometry(self, include_features=True):
        # type: (bool) -> compas.datastructures.Mesh | compas.geometry.Brep
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the base geometry.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """
        blank_geo = self.shape
        if include_features:
            for feature in self.features:
                try:
                    blank_geo = feature.apply(blank_geo)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        return blank_geo

    def compute_aabb(self, inflate=0.0):
        # type: (float) -> compas.geometry.Box
        """Computes the Axis Aligned Bounding Box (AABB) of the element.

        Parameters
        ----------
        inflate : float, optional
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The AABB of the element.

        """
        vertices = [point for point in self.outline.points]
        for point in self.outline.points:
            vertices += point + self.vector
        box = Box.from_bounding_box(bounding_box(vertices))
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

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
        obb = self.blank.copy()
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        return obb

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.blank.to_mesh()

    # ==========================================================================
    # Alternative constructors
    # ==========================================================================


    @staticmethod
    def _create_shape(outline, vector):

        brep = Brep.from_extrusion(outline, vector)

        return brep

    # ==========================================================================
    # Featrues
    # ==========================================================================

    @reset_computed
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

    @reset_computed
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
