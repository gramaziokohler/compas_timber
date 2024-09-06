from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import dot_vectors
from compas_model.elements import Element
from compas_model.elements import reset_computed

from .features import FeatureApplicationError


class Plate(Element):
    """
    A class to represent timber plates (plywood, CLT, etc.) with uniform thickness.

    Parameters
    ----------
    outline : :class:`~compas.geometry.RhinoCurve`
        A line representing the outline of this plate.
    thickness : float
        Thickness of the plate material.
    vector : :class:`~compas.geometry.Vector`, optional
        The vector of the plate. Default is None.


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

    @property
    def __data__(self):
        data = super(Plate, self).__data__
        data["outline"] = self.outline
        data["thickness"] = self.thickness
        data["vector"] = self.vector
        return data

    def __init__(self, outline, thickness, vector=None, frame=None, **kwargs):
        super(Plate, self).__init__(**kwargs)
        if not outline.is_closed:
            raise ValueError("The outline points are not coplanar.")
        self.outline = outline
        self.thickness = thickness
        self.set_frame_and_outline(outline, vector)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Plate(outline={!r}, thickness={})".format(self.outline, self.thickness)

    def __str__(self):
        return "Plate {} with thickness {:.3f} with vector {} at {}".format(
            self.outline,
            self.thickness,
            self.vector,
            self.frame,
        )

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def blank(self):
        return self.obb

    @property
    def vector(self):
        return self.frame.zaxis * self.thickness

    @property
    def shape(self):
        brep = Brep.from_extrusion(self.outline, self.vector)
        return brep

    @property
    def has_features(self):
        # TODO: move to compas_future... Part
        return len(self.features) > 0

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def set_frame_and_outline(self, outline, vector=None):
        frame = Frame.from_points(outline.points[0], outline.points[1], outline.points[-2])
        aggregate_angle = 0.0  # this is used to determine if the outline is clockwise or counterclockwise
        for i in range(len(outline.points) - 1):
            first_vector = Vector.from_start_end(outline.points[i - 1], outline.points[i])
            second_vector = Vector.from_start_end(outline.points[i], outline.points[i + 1])
            aggregate_angle += angle_vectors_signed(first_vector, second_vector, frame.zaxis)
        if aggregate_angle > 0:
            frame = Frame(frame.point, frame.xaxis, -frame.yaxis)
            # flips the frame if the frame.point is at an interior corner

        if vector is not None and dot_vectors(frame.zaxis, vector) < 0:
            # if the vector is pointing in the opposite direction from self.frame.normal
            frame = Frame(frame.point, frame.yaxis, frame.xaxis)
            self.outline.reverse()
            # flips the frame if the frame.point is at an exterior corner

        self.frame = frame

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
        plate_geo = self.shape
        if include_features:
            for feature in self.features:
                try:
                    plate_geo = feature.apply(plate_geo)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        return plate_geo

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
            vertices.append(point + self.vector)
        box = Box.from_points(vertices)
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
        vertices = [point for point in self.outline.points]
        for point in self.outline.points:
            vertices.append(point + self.vector)
        for point in vertices:
            point.transform(Transformation.from_change_of_basis(Frame.worldXY(), self.frame))
        obb = Box.from_points(vertices)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate

        obb.transform(Transformation.from_change_of_basis(self.frame, Frame.worldXY()))

        return obb

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.obb.to_mesh()

    # ==========================================================================
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
