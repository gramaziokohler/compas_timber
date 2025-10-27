from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_model.elements import reset_computed

from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import FreeContour

from .plate_geometry import PlateGeometry
from .timber import TimberElement


class Plate(PlateGeometry, TimberElement):
    """
    A class to represent timber plates (plywood, CLT, etc.) defined by polylines on top and bottom faces of material.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    length : float
        Length of the plate.
    width : float
        Width of the plate.
    thickness : float
        Thickness of the plate.
    outline_a : :class:`~compas.geometry.Polyline`, optional
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`, optional
        A line representing the associated outline of this plate. This should have the same number of points as outline_a.
    openings : list[:class:`~compas.geometry.Polyline`], optional
        A list of Polyline objects representing openings in this plate.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate.
    length : float
        Length of the plate.
    width : float
        Width of the plate.
    height : float
        Height of the plate (same as thickness).
    thickness : float
        Thickness of the plate.
    is_plate : bool
        Always True for plates.
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this plate.
    blank_length : float
        Length of the plate blank.
    features : list[:class:`~compas_timber.fabrication.Feature`]
        List of features applied to this plate.
    shape : :class:`~compas.geometry.Brep`
        The geometry of the Plate before other machining features are applied.
    ref_frame : :class:`~compas.geometry.Frame`
        Reference frame for machining processings according to BTLx standard.
    ref_sides : tuple[:class:`~compas.geometry.Frame`, ...]
        A tuple containing the 6 frames representing the sides of the plate according to BTLx standard.
    key : int, optional
        Once plate is added to a model, it will have this model-wide-unique integer key.

    """

    @property
    def __data__(self):
        data = TimberElement.__data__(self)
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        data["openings"] = [o.__data__ for o in self.openings]
        return data

    def __init__(self, frame, length, width, thickness, local_outline_a=None, local_outline_b=None, openings=None, **kwargs):
        TimberElement.__init__(self, frame=frame, length=length, width=width, height=thickness, **kwargs)
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        PlateGeometry.__init__(self, local_outline_a, local_outline_b, openings=openings)
        self._outline_feature = None
        self._opening_features = None
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

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
        """Check if this element is a plate.

        Returns
        -------
        bool
            Always True for plates.
        """
        return True

    @property
    def blank(self):
        """A feature-less box representing the material stock geometry to produce this plate.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The blank box of the plate.
        """
        box = Box.from_points(self.local_outlines[0].points + self.local_outlines[1].points)
        box.translate(self.frame.point - box.points[0])
        box.xsize += 2 * self.attributes.get("blank_extension", 0.0)
        box.ysize += 2 * self.attributes.get("blank_extension", 0.0)
        return box

    @property
    def blank_length(self):
        """Length of the plate blank.

        Returns
        -------
        float
            The length of the blank.
        """
        return self.blank.xsize

    @property
    def features(self):
        """All features of the plate including outline, openings, and user-defined features.

        Returns
        -------
        list[:class:`~compas_timber.fabrication.Feature`]
            A list of all features applied to this plate.
        """
        if not self._outline_feature:
            self._outline_feature = FreeContour.from_top_bottom_and_elements(self.outline_a, self.outline_b, self, interior=False)
        if not self._opening_features:
            self._opening_features = [FreeContour.from_polyline_and_element(o.transformed(Transformation.from_frame(self.frame)), self, interior=True) for o in self.openings]
        return [self._outline_feature] + self._opening_features + self._features

    @features.setter
    def features(self, features):
        # type: (list[FreeContour]) -> None
        """Sets the features of the plate."""
        self._features = features

    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        PlateGeometry.reset(self)  # reset outline_a and outline_b
        self._features = []
        self._outline_feature = None
        self._opening_features = None
        self.debug_info = []

    # ==========================================================================
    #  Implementation of abstract methods
    # ==========================================================================

    def compute_geometry(self, include_features=True):
        # type: (bool) -> compas.geometry.Brep
        """Compute the geometry of the element in global coordinates.

        Parameters
        ----------
        include_features : bool, optional
            If True, the features should be included in the element geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`

        Raises
        ------
        :class:`compas_timber.errors.FeatureApplicationError`
            If there is an error applying features to the element.

        """

        # TODO: consider if Brep.from_curves(curves) is faster/better
        plate_geo = self.shape
        if include_features:
            for feature in self._features:
                try:
                    plate_geo = feature.apply(plate_geo, self)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        return plate_geo.transformed(Transformation.from_frame(self.frame))

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, **kwargs):
        """
        Constructs a PlateGeometry from two polyline outlines. to be implemented to instantialte Plates and Slabs.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the plate geometry in parent space.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the plate geometry in parent space.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of openings to be added to the plate geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.PlateGeometry`
            A PlateGeometry object representing the plate geometry with the given outlines.
        """
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, openings)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        kwargs.update(args)
        return cls(**kwargs)
