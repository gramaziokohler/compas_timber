from compas_model.elements import reset_computed
from compas.geometry import Frame

from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import FreeContour


from .timber import TimberElement
from .plate_geometry import PlateGeometry

class Plate(PlateGeometry, TimberElement):
    """
    A class to represent timber plates (plywood, CLT, etc.) defined by polylines on top and bottom faces of material.

    Parameters
    ----------
    outline_a : :class:`~compas.geometry.Polyline`                                                  TODO: add support for NurbsCurve
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate. This should have the same number of points as outline_a.


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
        return super(Plate, self).__data__

    def __init__(self, outline_a=None, outline_b=None, openings=None, frame=None, **kwargs):
        PlateGeometry.__init__(self, outline_a, outline_b, openings=openings, frame=frame)
        TimberElement.__init__(self, **kwargs)
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
        return True

    @property
    def blank(self):
        _blank = self.obb.copy()
        _blank.xsize += 2 * self.attributes.get("blank_extension", 0.0)
        _blank.ysize += 2 * self.attributes.get("blank_extension", 0.0)
        return _blank

    @property
    def blank_length(self):
        return self.blank.xsize

    @property
    def ref_frame(self):
        return Frame(self.blank.points[0], self.frame.xaxis, self.frame.yaxis)


    @property
    def features(self):
        if not self._outline_feature:
            self._outline_feature = FreeContour.from_top_bottom_and_elements(self.local_outlines[0], self.local_outlines[1], self, interior=False)
        if not self._opening_features:
            self._opening_features = [FreeContour.from_top_bottom_and_elements(o.outline_a, o.outline_b, self, interior=True) for o in self.openings]
        return [self._outline_feature] + self._opening_features + self._features

    @features.setter
    def features(self, features):
        # type: (list[FreeContour]) -> None
        """Sets the features of the plate."""
        self._features = features


    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        super(Plate, self).reset() #reset outline_a and outline_b
        self._features = []
        self._outline_feature = None
        self._opening_features = None
        self.debug_info = []



    # ==========================================================================
    #  Implementation of abstract methods
    # ==========================================================================



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
        plate_geo = self.compute_elementgeometry(include_features=include_features)
        return plate_geo.transformed(self.transformation)

    def compute_elementgeometry(self, include_features=True):
        # type: (bool) -> compas.datastructures.Mesh | compas.geometry.Brep
        """Compute the geometry of the element.

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
        return plate_geo

