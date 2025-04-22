from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import PlanarSurface
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.tolerance import TOL
from compas_model.elements import reset_computed

from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import FreeContour
from compas_timber.utils import is_polyline_clockwise

from .timber import TimberElement


class Plate(TimberElement):
    """
    A class to represent timber plates (plywood, CLT, etc.) defined by polylines on top and bottom faces of material.

    Parameters
    ----------
    outline_a : :class:`~compas.geometry.Polyline`                                                  TODO: add support for NurbsCurve
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate. This should have the same number of points as outline_a.
    blank_extension : float, optional
        The extension of the blank geometry around the edges of the plate geometry. Default is 0.


    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate.
    blank_length : float
        Length of the plate blank.
    width : float
        Thickness of the plate material.
    height : float
        Height of the plate blank.
    shape : :class:`~compas.geometry.Brep`
        The geometry of the Plate before other machining features are applied.
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this plate.
    ref_frame : :class:`~compas.geometry.Frame`
        Reference frame for machining processings according to BTLx standard.
    ref_sides : tuple(:class:`~compas.geometry.Frame`)
        A tuple containing the 6 frames representing the sides of the plate according to BTLx standard.
    aabb : tuple(float, float, float, float, float, float)
        An axis-aligned bounding box of this plate as a 6 valued tuple of (xmin, ymin, zmin, xmax, ymax, zmax).
    key : int, optional
        Once plate is added to a model, it will have this model-wide-unique integer key.

    """

    @property
    def __data__(self):
        data = super(Plate, self).__data__
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["blank_extension"] = self.blank_extension
        return data

    def __init__(self, outline_a, outline_b, blank_extension=0, **kwargs):
        super(Plate, self).__init__(**kwargs)
        if not TOL.is_allclose(outline_a[0], outline_a[-1]):
            raise ValueError("The outline_a is not closed.")
        if not TOL.is_allclose(outline_b[0], outline_b[-1]):
            raise ValueError("The outline_b is not closed.")
        if len(outline_a) != len(outline_b):
            raise ValueError("The outlines have different number of points.")
        self.outline_a = outline_a
        self.outline_b = outline_b
        self._outline_feature = None
        self._frame = None
        self.blank_extension = blank_extension
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self._ref_frame = None
        self._blank = None
        self._features = []

    def __repr__(self):
        # type: () -> str
        return "Plate(outline_a={!r}, outline_b={!r})".format(self.outline_a, self.outline_b)

    def __str__(self):
        return "Plate {}, {} ".format(self.outline_a, self.outline_b)

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
                self._blank.xsize += 2 * self.blank_extension
                self._blank.ysize += 2 * self.blank_extension
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
            self._ref_frame = Frame(self.blank.points[0], self.frame.xaxis, self.frame.yaxis)
        return self._ref_frame

    @property
    def ref_sides(self):
        # type: () -> tuple[Frame, Frame, Frame, Frame, Frame, Frame]
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        # TODO: cache these
        rs1_point = self.ref_frame.point
        rs2_point = rs1_point + self.ref_frame.yaxis * self.height
        rs3_point = rs1_point + self.ref_frame.yaxis * self.height + self.ref_frame.zaxis * self.width
        rs4_point = rs1_point + self.ref_frame.zaxis * self.width
        rs5_point = rs1_point
        rs6_point = rs1_point + self.ref_frame.xaxis * self.blank_length + self.ref_frame.yaxis * self.height
        return (
            Frame(rs1_point, self.ref_frame.xaxis, self.ref_frame.zaxis, name="RS_1"),
            Frame(rs2_point, self.ref_frame.xaxis, -self.ref_frame.yaxis, name="RS_2"),
            Frame(rs3_point, self.ref_frame.xaxis, -self.ref_frame.zaxis, name="RS_3"),
            Frame(rs4_point, self.ref_frame.xaxis, self.ref_frame.yaxis, name="RS_4"),
            Frame(rs5_point, self.ref_frame.zaxis, self.ref_frame.yaxis, name="RS_5"),
            Frame(rs6_point, self.ref_frame.zaxis, -self.ref_frame.yaxis, name="RS_6"),
        )

    def side_as_surface(self, side_index):
        # type: (int) -> compas.geometry.PlanarSurface
        """Returns the requested side of the beam as a parametric planar surface.

        Parameters
        ----------
        side_index : int
            The index of the reference side to be returned. 0 to 5.

        """
        # TODO: maybe this should be the default representation of the ref sides?
        ref_side = self.ref_sides[side_index]
        if side_index in (0, 2):  # top + bottom
            xsize = self.blank_length
            ysize = self.width
        elif side_index in (1, 3):  # sides
            xsize = self.blank_length
            ysize = self.height
        elif side_index in (4, 5):  # ends
            xsize = self.width
            ysize = self.height
        return PlanarSurface(xsize, ysize, frame=ref_side, name=ref_side.name)

    @property
    def features(self):
        if not self._outline_feature:
            self._outline_feature = FreeContour.from_top_bottom_and_elements(self.outline_a, self.outline_b, self, interior=False)
        return [self._outline_feature] + self._features

    @features.setter
    def features(self, features):
        self._features = features

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    @property
    def frame(self):
        if not self._frame:
            self._frame = Frame.from_points(self.outline_a[0], self.outline_a[1], self.outline_a[-2])
            if is_polyline_clockwise(self.outline_a, self._frame.normal):
                self._frame = Frame(self._frame.point, self._frame.xaxis, -self._frame.yaxis)
        return self._frame
        # flips the frame if the frame.point is at an interior corner

    # ==========================================================================
    # Alternate constructors
    # ==========================================================================

    @classmethod
    def from_outline_thickness(cls, outline, thickness, vector=None, blank_extension=0, **kwargs):
        """
        Constructs a plate from a polyline outline and a thickness.
        The outline is the top face of the plate, and the thickness is the distance to the bottom face.

        Parameters
        ----------
        outline : :class:`~compas.geometry.Polyline`
            A polyline representing the outline of the plate.
        thickness : float
            The thickness of the plate.
        vector : :class:`~compas.geometry.Vector`, optional
            The direction of the thickness vector. If None, the thickness vector is determined from the outline.
        blank_extension : float, optional
            The extension of the blank geometry around the edges of the plate geometry. Default is 0.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Plate`
            A Plate object representing the plate with the given outline and thickness.
        """
        # this ensure the plate's geometry can always be computed
        if TOL.is_zero(thickness):
            thickness = TOL.absolute

        # TODO: @obucklin `vector` is never actually used here, at most it is used to determine the direction of the thickness vector which is always calculated from the outline.
        # TODO: is this the intention? should it maybe be replaced with some kind of a boolean flag?
        thickness_vector = Frame.from_points(outline[0], outline[1], outline[-2]).normal
        if vector and thickness_vector.dot(vector) < 0:
            thickness_vector = -thickness_vector
        thickness_vector.unitize()
        thickness_vector *= thickness
        outline_b = Polyline(outline).translated(thickness_vector)
        return cls(outline, outline_b, blank_extension=blank_extension, **kwargs)

    # ==========================================================================
    #  methods
    # ==========================================================================

    def add_feature(self, feature):
        # type: (compas_timber.parts.Feature) -> None
        """Adds a feature to the plate.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature`
            The feature to be added.

        """
        self._features.append(feature)

    def shape(self):
        # type: () -> compas.geometry.Brep
        """The shape of the plate before other features area applied.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The shape of the element.

        """
        plate_geo = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (self.outline_a, self.outline_b)])
        plate_geo.cap_planar_holes()
        return plate_geo

    def compute_geometry(self, include_features=True):
        # type: (bool) -> compas.datastructures.Mesh | compas.geometry.Brep
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the plate shape.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """

        # TODO: consider if Brep.from_curves(curves) is faster/better
        plate_geo = self.shape()
        if include_features:
            for feature in self._features:
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
        vertices = self.outline_a.points + self.outline_b.points
        box = Box.from_points(vertices)
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def compute_obb(self, inflate=0.0):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """
        vertices = self.outline_a.points + self.outline_b.points
        world_vertices = []
        for point in vertices:
            world_vertices.append(point.transformed(Transformation.from_frame_to_frame(self.frame, Frame.worldXY())))
        obb = Box.from_points(world_vertices)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        obb.transform(Transformation.from_frame_to_frame(Frame.worldXY(), self.frame))
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
        self._features.extend(features)

    @reset_computed
    def remove_features(self, features=None):
        """Removes a feature from the plate.

        Parameters
        ----------
        feature : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be removed. If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self._features = [f for f in self._features if f not in features]
