import abc
from functools import wraps

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_model.elements import Element
from compas_model.elements import reset_computed


def reset_timber_attrs(f):
    """Decorator to reset cached timber-specific attributes."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        self: TimberElement = args[0]
        self._blank = None
        self._ref_frame = None
        self._geometry = None  # from Element
        return f(*args, **kwargs)

    return wrapper


class TimberElement(Element, abc.ABC):
    """Base class for all timber elements.

    This is an abstract class and should not be instantiated directly.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`, optional
        The frame representing the beam's local coordinate system in its hierarchical context.
        Defaults to ``None``, in which case the world coordinate system is used.
    length : float
        Length of the timber element.
    width : float
        Width of the timber element.
    height : float
        Height of the timber element.
    features : list[:class:`~compas_timber.fabrication.Feature`], optional
        List of features to apply to this element.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`compas.geometry.Frame`
        The coordinate system of this element in model space.
        This property may be different from the constructor parameter if the element belongs to a model hierarchy.
    is_beam : bool
        True if the element is a beam.
    is_plate : bool
        True if the element is a plate.
    is_group_element : bool
        True if the element can be used as container for other elements.
    features : list[:class:`~compas_timber.parts.Feature`]
        A list of features applied to the element.
    geometry : :class:`compas.geometry.Geometry`
        The geometry of the element in the model's global coordinates.

    """

    @property
    def __data__(self):
        data = {}
        data["frame"] = self.frame
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["features"] = [f for f in self.features if not f.is_joinery]  # type: ignore
        data.update(self.attributes)
        return data

    def __init__(self, frame, length, width, height, features=None, **kwargs):
        super().__init__(transformation=Transformation.from_frame(frame), features=features)
        self.attributes = {}
        self.attributes.update(kwargs)
        self.length = length
        self.width = width
        self.height = height
        self._blank = None
        self._ref_frame = None
        self.debug_info = []

    @reset_computed
    @reset_timber_attrs
    def _reset_computed_dummy(self):
        """Dummy method to trigger reset_computed decorator."""
        pass

    def reset_computed_properties(self):
        """Reset all computed/cached properties."""
        self._reset_computed_dummy()

    @property
    def is_beam(self):
        return False

    @property
    def is_plate(self):
        return False

    @property
    def is_group_element(self):
        # NOTE: I left this in for now, but in the new compas_model, any element can be a container/parent.
        return False

    @property
    def features(self):
        # type: () -> list[BTLxProcessing]
        return self._features

    @features.setter
    @reset_computed
    def features(self, features):
        self._features = features

    @reset_timber_attrs
    def transform(self, transformation):
        # override to reset timber-specific cached attributes
        super().transform(transformation)

    @property
    def geometry(self):
        """The geometry of the element in the model's global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_modelgeometry()
        return self._geometry

    # ========================================================================
    # Geometry computation methods
    # ========================================================================

    def compute_modeltransformation(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()

    def compute_modelgeometry(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)
        return super().compute_modelgeometry()

    # ========================================================================
    # Feature management & Modification methods
    # ========================================================================

    def remove_blank_extension(self):
        """Remove blank extension from the element.

        This method is intended to be overridden by subclasses.
        """
        pass

    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.remove_features()
        self.remove_blank_extension()
        self.debug_info = []

    @reset_computed
    @reset_timber_attrs
    def add_feature(self, feature):
        # type: (BTLxProcessing) -> None
        """Adds one or more features to the beam.

        Parameters
        ----------
        feature : :class:`~compas_timber.fabrication.BTLxProcessing`)
            The feature to be added.

        """
        self._features.append(feature)  # type: ignore

    @reset_computed
    @reset_timber_attrs
    def add_features(self, features):
        # type: (BTLxProcessing | list[BTLxProcessing]) -> None
        """Adds one or more features to the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.fabrication.BTLxProcessing` | list(:class:`~compas_timber.fabrication.BTLxProcessing`)
            The feature or features to be added described as a BTLxProcessing or a list of BTLxProcessings.

        """
        if not isinstance(features, list):
            features = [features]
        self._features.extend(features)  # type: ignore

    @reset_computed
    @reset_timber_attrs
    def remove_features(self, features=None):
        # type: (None | BTLxProcessing | list[BTLxProcessing]) -> None
        """Removes a feature from the beam.

        Parameters
        ----------
        feature : :class:`~compas_timber.fabrication.BTLxProcessing` | list(:class:`~compas_timber.fabrication.BTLxProcessing`) | None
            The feature or features to be removed described as a BTLxProcessing or a list of BTLxProcessings.
            If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self._features = [f for f in self._features if f not in features]

    def transformation_to_local(self):
        """Compute the transformation to local coordinates of this element
        based on its position in the spatial hierarchy of the model.

        Returns
        -------
        :class:`compas.geometry.Transformation`

        """
        # type: () -> Transformation
        return self.modeltransformation.inverted()

    ########################################################################
    # BTLx properties
    ########################################################################

    @property
    def ref_frame(self):
        # type: () -> Frame
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        """
        Reference frame for machining processings according to BTLx standard.
        The origin is at the bottom far corner of the element.
        The ref_frame is always in model coordinates.
        """
        if not self._ref_frame:
            self._ref_frame = Frame(
                self.blank.points[1], Vector.from_start_end(self.blank.points[1], self.blank.points[2]), Vector.from_start_end(self.blank.points[1], self.blank.points[7])
            )
        return self._ref_frame

    @property
    def ref_sides(self):
        # type: () -> tuple[Frame, Frame, Frame, Frame, Frame, Frame]
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
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

    @property
    def ref_edges(self):
        # type: () -> tuple[Line, Line, Line, Line]
        # so tuple is not created every time
        ref_sides = self.ref_sides
        return (
            Line(ref_sides[0].point, ref_sides[0].point + ref_sides[0].xaxis * self.blank_length, name="RE_1"),
            Line(ref_sides[1].point, ref_sides[1].point + ref_sides[1].xaxis * self.blank_length, name="RE_2"),
            Line(ref_sides[2].point, ref_sides[2].point + ref_sides[2].xaxis * self.blank_length, name="RE_3"),
            Line(ref_sides[3].point, ref_sides[3].point + ref_sides[3].xaxis * self.blank_length, name="RE_4"),
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

    def front_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the next side after the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the front side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the front side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index + 1) % 4]

    def back_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the previous side before the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the back side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the back side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index - 1) % 4]

    def opp_side(self, ref_side_index):
        # type: (int) -> Frame
        """Returns the the side that is directly across from the reference side, following the right-hand rule with the thumb along the beam's frame x-axis.
        This method does not consider the start and end sides of the beam (RS5 & RS6).

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the opposite side should be calculated.

        Returns
        -------
        frame : :class:`~compas.geometry.Frame`
            The frame of the opposite side of the beam relative to the reference side.
        """
        return self.ref_sides[(ref_side_index + 2) % 4]

    def get_dimensions_relative_to_side(self, ref_side_index):
        # type: (int) -> tuple[float, float]
        """Returns the perpendicular and parallel dimensions of the beam to the given reference side.

        Parameters
        ----------
        ref_side_index : int
            The index of the reference side to which the dimensions should be calculated.

        Returns
        -------
        tuple(float, float)
            The perpendicular and parallel dimensions of the beam to the reference side.
                - Perpendicular dimension: The measurement normal to the reference side.
                - Parallel dimension: The measurement along y-axis of reference side.
        """
        if ref_side_index in [1, 3]:
            return self.height, self.width
        return self.width, self.height
