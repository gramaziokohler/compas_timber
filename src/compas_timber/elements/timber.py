from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Transformation
from compas.geometry import Translation
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
        transformation = Transformation.from_frame(self.frame) if self.frame else Transformation()
        if self.is_beam:
            # For beams, we need to apply the blank extension to the transformation
            # This is needed to align the beam's geometry with the model's coordinate system
            # The blank extension is applied to the start of the beam
            start, _ = self._resolve_blank_extensions()
            transformation *= Translation.from_vector(-self.frame.xaxis * start)
        return transformation

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
        # this property return the geometry of the element in it's own global coordinates.
        # since the element doesn't know anything about the tree, those coordinates might differ from the model's coordinate system.
        if self._geometry is None:
            element_geometry = self.compute_elementgeometry()
            self._geometry = element_geometry.transformed(self.transformation)
        return self._geometry

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
        self._geometry = None  # reset geometry cache TODO: should we do that?

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
        self._geometry = None  # reset geometry cache TODO: should we do that?

    ########################################################################
    # BTLx properties
    ########################################################################

    @property
    def ref_frame(self):
        # type: () -> Frame
        # See: https://design2machine.com/btlx/BTLx_2_2_0.pdf
        """Reference frame for machining processings according to BTLx standard. The origin is at the bottom far corner of the element."""
        # TODO: check if this applies for other elements than beams -> plate
        assert self.frame
        start, _ = self._resolve_blank_extensions()
        ref_point = self.frame.point.copy()
        ref_point += -self.frame.xaxis * start  # "extension" to the start edge

        ref_point += self.frame.yaxis * self.width * 0.5
        ref_point -= self.frame.zaxis * self.height * 0.5
        return Frame(ref_point, self.frame.xaxis, self.frame.zaxis)

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
