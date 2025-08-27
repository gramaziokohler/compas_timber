from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import PlanarSurface
from compas.geometry import Transformation
from compas_model.elements import Element
from compas_model.elements import reset_computed


class TimberElement(Element):
    """Base class for all timber elements.

    This is an abstract class and should not be instantiated directly.

    Attributes
    ----------
    is_beam : bool
        True if the element is a beam.
    is_plate : bool
        True if the element is a plate.
    is_wall : bool
        True if the element is a wall.
    is_group_element : bool
        True if the element can be used as container for other elements.

    """

    @property
    def __data__(self):
        data = super(TimberElement, self).__data__
        data["features"] = [f for f in self.features if not f.is_joinery]  # type: ignore
        return data

    def __init__(self, features=None, **kwargs):
        super(TimberElement, self).__init__(**kwargs)
        self._features = features or []
        self._geometry = None
        self.debug_info = []

    @property
    def is_beam(self):
        return False

    @property
    def is_plate(self):
        return False

    @property
    def is_wall(self):
        return False

    @property
    def is_group_element(self):
        return False

    @property
    def is_fastener(self):
        return False

    @property
    def is_opening(self):
        return False

    @property
    def frame(self):
        # type: () -> Frame | None
        """The local coordinate system of the element."""
        return self._frame

    @frame.setter
    def frame(self, frame):
        # type: (Frame) -> None
        self._frame = frame

    @property
    def transformation(self):
        # type: () -> Transformation
        """The transformation that transforms the element's geometry to the model's coordinate system."""
        return Transformation.from_frame(self.frame) if self.frame else Transformation()

    @property
    def features(self):
        # type: () -> list[Feature]
        """A list of features applied to the element."""
        return self._features

    @features.setter
    @reset_computed
    def features(self, features):
        self._features = features

    @property
    def geometry(self):
        """The geometry of the element in its own global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_geometry(include_features=True)
        return self._geometry

    # ========================================================================
    # Geometry computation methods
    # ========================================================================

    def compute_geometry(self, include_features=False):
        # type: (bool) -> compas.geometry.Brep
        """Compute the geometry of the element in global coordinates.

        This is the parametric representation of the element,
        considering its location in the model.

        Parameters
        ----------
        include_features : bool, optional
            If True, the features should be included in the element geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The geometry of the element in global coordinates.

        Raises
        ------
        FeatureApplicationError
            If there is an error applying features to the element.

        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def compute_elementgeometry(self, include_features=False):
        # type: (bool) -> compas.geometry.Brep
        """Compute the geometry of the element in local coordinates.

        This is the parametric representation of the element,
        without considering its location in the model.

        Parameters
        ----------
        include_features : bool, optional
            If True, the features should be included in the element geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`

        """
        global_geo = self.compute_geometry(include_features=include_features)
        if global_geo:
            return global_geo.transformed(self.transformation.inverse())

    # ========================================================================
    # Feature management & Modification methods
    # ========================================================================

    def remove_blank_extension(self):
        pass

    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.remove_features()
        self.remove_blank_extension()
        self.debug_info = []

    @reset_computed
    def add_features(self, features):
        # type: (Feature | list[Feature]) -> None
        """Adds one or more features to the beam.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list(:class:`~compas_timber.parts.Feature`)
            The feature to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self._features.extend(features)  # type: ignore
        self._geometry = None  # reset geometry cache

    @reset_computed
    def remove_features(self, features=None):
        # type: (None | Feature | list[Feature]) -> None
        """Removes a feature from the beam.

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
        self._geometry = None  # reset geometry cache

    ########################################################################
    # BTLx properties
    ########################################################################

    @property
    def ref_frame(self):
        # type: () -> Frame
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        """Reference frame for machining processings according to BTLx standard. The origin is at the bottom far corner of the element."""

        raise NotImplementedError("This method should be implemented by subclasses.")

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




class TimberGroupElement:
    def __init__(self, features=None, elements=None, **kwargs):
        super(TimberElement, self).__init__(features=features, **kwargs)
        self._elements = elements or []

    def add_element(self, element, transform_element=True):
        print("group frame = ", self.frame)
        print("adding element", element.name)
        if transform_element:
            print("element frame = ", element.frame)
            element.frame.transform(self.transformation.inverse())
            print("group transoformation = ", self.transformation)
            print("transformed element frame = ", element.frame)
            self._elements.append(element)
        else:
            self._elements.append(element)
        print("slab.elements contains:", [e.name for e in self.elements])
        print(element.transformation)

    def remove_element(self, element):
        self.elements.remove(element)

    @property
    def elements(self):
        return self._elements
