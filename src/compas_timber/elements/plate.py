from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import dot_vectors
from compas_model.elements import reset_computed

from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import FreeContour
from compas_timber.utils import correct_polyline_direction, is_polyline_clockwise

from .timber import TimberElement


class Plate(TimberElement):
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
    key : int, optional
        Once plate is added to a model, it will have this model-wide-unique integer key.

    """

    @property
    def __data__(self):
        data = super(Plate, self).__data__
        data["outline"] = self.outline
        data["thickness"] = self.thickness
        data["vector"] = self.vector
        return data

    def __init__(self, outline, thickness, vector=None, frame=None, blank_extension = 0, **kwargs):
        super(Plate, self).__init__(**kwargs)
        if not outline.is_closed:
            raise ValueError("The outline is not closed.")
        self.blank_extension = blank_extension
        self.thickness = thickness
        self.outline = outline
        self._vector = vector or None
        self._frame = frame or None
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self._ref_frame = None
        self._blank = None
        self.correct_outline()
        contour_feature = FreeContour.from_polyline_and_element(self.outline, self, interior=False)
        self.add_feature(contour_feature)

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
    def is_plate(self):
        return True

    @property
    def blank(self):
        if not self._blank:
            self._blank = self.obb.copy()
            if self.blank_extension:
                self._blank.xsize += 2*self.blank_extension
                self._blank.ysize += 2*self.blank_extension
        return self._blank

    @property
    def blank_length(self):
        return self.blank.xsize

    @property
    def width(self):
        return self.blank.zsize

    @property
    def height(self):
        return self.blank.ysize

    @property
    def ref_frame(self):
        if not self._ref_frame:
            print(self.blank.xmin, self.blank.ymin, self.blank.zmin)
            self._ref_frame = Frame(self.blank.points[0], self.frame.xaxis, self.frame.yaxis)
        return self._ref_frame

    @property
    def has_features(self):
        # TODO: consider removing, this is not used anywhere
        return len(self.features) > 0

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    @property
    def frame(self):
        if not self._frame:
            self._frame = Frame.from_points(self.outline[0], self.outline[1], self.outline[-2])
            if is_polyline_clockwise(self.outline, self._frame.normal):
                self._frame = Frame(self._frame.point, self._frame.xaxis, -self._frame.yaxis)
        return self._frame
            # flips the frame if the frame.point is at an interior corner

    @property
    def vector(self):
        if not self._vector:
            self._vector = self.frame.zaxis * self.thickness
        return self._vector




    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def correct_outline(self):
        self.outline = correct_polyline_direction(self.outline, self.vector)

    def compute_geometry(self, include_features=True):
        # type: (bool) -> compas.datastructures.Mesh | compas.geometry.Brep
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the outline geometry.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """
        plate_geo = Brep.from_extrusion(self.outline, self.vector)
        include_features = False
        if include_features:
            for feature in self.features:
                try:
                    plate_geo = feature.apply(plate_geo, self)
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

    def compute_obb(self):
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
        vertices = []
        for point in self.outline:
            vertices.append(point.transformed(Transformation.from_frame_to_frame(self.frame, Frame.worldXY())))
        obb = Box.from_points(vertices)
        obb.zsize = self.thickness
        obb.translate([0, 0, self.thickness / 2])
        xform_back = Transformation.from_frame_to_frame(Frame.worldXY(), self.frame)
        obb.transform(xform_back)
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
