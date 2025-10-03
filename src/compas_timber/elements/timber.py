from compas.geometry import Frame
from compas.geometry import Line
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
        data["frame"] = self.frame
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["features"] = [f for f in self.features if not f.is_joinery]  # type: ignore
        return data

    def __init__(self, frame, length, width, height, features=None, **kwargs):
        """Initialize a TimberElement.
        
        Parameters
        ----------
        frame : :class:`~compas.geometry.Frame`
            The coordinate system (frame) of this timber element.
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
        """
        super(TimberElement, self).__init__(**kwargs)
        self.frame = frame
        self.length = length
        self.width = width
        self.height = height
        self._features = features or []
        self.debug_info = []

    @property
    def is_beam(self):
        """Check if this element is a beam.
        
        Returns
        -------
        bool
            False for the base TimberElement class.
        """
        return False

    @property
    def is_plate(self):
        """Check if this element is a plate.
        
        Returns
        -------
        bool
            False for the base TimberElement class.
        """
        return False

    @property
    def is_group_element(self):
        """Check if this element can be used as a container for other elements.
        
        Returns
        -------
        bool
            False for the base TimberElement class.
        """
        return False

    @property
    def features(self):
        """List of features applied to this element.
        
        Returns
        -------
        list[:class:`~compas_timber.fabrication.Feature`]
            The features applied to this element.
        """
        # type: () -> list[Feature]
        return self._features

    @features.setter
    def features(self, features):
        self._features = features

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
    def add_features(self, features):
        # type: (Feature | list[Feature]) -> None
        """Adds one or more features to the element.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list[:class:`~compas_timber.parts.Feature`]
            The features to be added.

        """
        if not isinstance(features, list):
            features = [features]
        self._features.extend(features)  # type: ignore

    @reset_computed
    def remove_features(self, features=None):
        # type: (None | Feature | list[Feature]) -> None
        """Removes features from the element.

        Parameters
        ----------
        features : :class:`~compas_timber.parts.Feature` | list[:class:`~compas_timber.parts.Feature`], optional
            The features to be removed. If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self._features = [f for f in self._features if f not in features]

    @property
    def ref_frame(self):
        """Reference frame for machining processing according to BTLx standard.
        
        Returns
        -------
        :class:`~compas.geometry.Frame`
            The reference frame of the element.
        """
        # type: () -> Frame
        return Frame(self.blank.points[1], self.frame.xaxis, self.frame.zaxis)

    @property
    def ref_sides(self):
        """The 6 frames representing the sides of the element according to BTLx standard.
        
        Returns
        -------
        tuple[:class:`~compas.geometry.Frame`, ...]
            A tuple containing the 6 frames representing the sides of the element.
        """
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
        """The 4 lines representing the long edges of the element according to BTLx standard.
        
        Returns
        -------
        tuple[:class:`~compas.geometry.Line`, ...]
            A tuple containing the 4 lines representing the long edges of the element.
        """
        # type: () -> tuple[Line, Line, Line, Line]
        # so tuple is not created every time
        ref_sides = self.ref_sides
        return (
            Line(ref_sides[0].point, ref_sides[0].point + ref_sides[0].xaxis * self.blank_length, name="RE_1"),
            Line(ref_sides[1].point, ref_sides[1].point + ref_sides[1].xaxis * self.blank_length, name="RE_2"),
            Line(ref_sides[2].point, ref_sides[2].point + ref_sides[2].xaxis * self.blank_length, name="RE_3"),
            Line(ref_sides[3].point, ref_sides[3].point + ref_sides[3].xaxis * self.blank_length, name="RE_4"),
        )
