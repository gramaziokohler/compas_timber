import os
from collections import OrderedDict

from compas.data import json_loadz
from compas.geometry import Frame
from compas.geometry import Scale
from compas.geometry import Transformation
from compas.tolerance import TOL

from compas_timber import DATA

from .btlx import AlignmentType
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams


class Text(BTLxProcessing):
    """Represents a Text feature to be made on a beam.

    Parameters
    ----------
    text : str
        The text to be engraved on the beam.
    start_x : float, optional
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0. Default is 0.0.
    start_y : float, optional
        The start y-coordinate of the cut in parametric space of the reference side. -50000.0 < start_y < 50000.0. Default is 0.0.
    angle : float, optional
        The horizontal angle of the first cut. -180.0 < angle < 180.0. Default is 0.0.
    alignment_vertical : {`AlignmentType.BOTTOM`, `AlignmentType.CENTER` or `AlignmentType.TOP`}, optional
        The vertical alignment of the text. Default is `AlignmentType.BOTTOM`.
    alignment_horizontal : {`AlignmentType.LEFT`, `AlignmentType.CENTER` or `AlignmentType.RIGHT`}, optional
        The horizontal alignment of the text. Default is `AlignmentType.LEFT`.
    alignment_multiline : {`AlignmentType.LEFT`, `AlignmentType.CENTER` or `AlignmentType.RIGHT`}, optional
        The alignment of the text in multiline mode. Default is `AlignmentType.LEFT`.
    stacked_marking : bool, optional
        If the text is a stacked marking. Default is False.
    text_height_auto : bool, optional
        If the text height is automatically calculated. Default is True.
    text_height : float, optional
        The height of the text. 0 < text_height < 50000.0. Default is 20.0.

    """

    PROCESSING_NAME = "Text"  # type: ignore
    _CHARACTER_DICT = {}

    @property
    def __data__(self):
        data = super(Text, self).__data__
        data["start_x"] = self.start_x
        data["start_y"] = self.start_y
        data["angle"] = self.angle
        data["alignment_vertical"] = self.alignment_vertical
        data["alignment_horizontal"] = self.alignment_horizontal
        data["alignment_multiline"] = self.alignment_multiline
        data["stacked_marking"] = self.stacked_marking
        data["text_height_auto"] = self.text_height_auto
        data["text_height"] = self.text_height
        data["text"] = self.text
        return data

    # fmt: off
    def __init__(
        self,
        text,
        start_x=0.0,
        start_y=0.0,
        angle=0.0,
        alignment_vertical=AlignmentType.BOTTOM,
        alignment_horizontal=AlignmentType.LEFT,
        alignment_multiline=AlignmentType.LEFT,
        stacked_marking=False,
        text_height_auto=True,
        text_height=20.0,
        **kwargs
    ):
        super(Text, self).__init__(**kwargs)
        self._start_x = None
        self._start_y = None
        self._angle = None
        self._alignment_vertical = None
        self._alignment_horizontal = None
        self._alignment_multiline = None
        self._stacked_marking = None
        self._text_height_auto = None
        self._text_height = None
        self._text = None

        self.start_x = start_x
        self.start_y = start_y
        self.angle = angle
        self.alignment_vertical = alignment_vertical
        self.alignment_horizontal = alignment_horizontal
        self.alignment_multiline = alignment_multiline
        self.stacked_marking = stacked_marking
        self.text_height_auto = text_height_auto
        self.text_height = text_height
        self.text = text


    @staticmethod
    def _load_character_dict():
        if not Text._CHARACTER_DICT:
            character_dict_path = os.path.join(DATA, "basic_characters.zip")
            Text._CHARACTER_DICT = json_loadz(character_dict_path)  # type: ignore


    ########################################################################
    # Properties
    ########################################################################

    @property
    def params(self):
        return TextParams(self)

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, value):
        if -100000 <= value <= 100000:
            self._start_x = value
        else:
            raise ValueError("Start x-coordinate should be between -100000 and 100000. Got: {}".format(value))

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, value):
        if -50000 <= value <= 50000:
            self._start_y = value
        else:
            raise ValueError("Start y-coordinate should be between -50000 and 50000. Got: {}".format(value))

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        if -180.0 <= value <= 180.0:
            self._angle = value
        else:
            raise ValueError("Angle should be between -180 and 180. Got: {}".format(value))

    @property
    def alignment_vertical(self):
        return self._alignment_vertical

    @alignment_vertical.setter
    def alignment_vertical(self, value):
        if value not in ("bottom", "center", "top"):
            raise ValueError("AlignmentVertical should be one of 'bottom', 'center', 'top'. Got: {}".format(value))
        self._alignment_vertical = value

    @property
    def alignment_horizontal(self):
        return self._alignment_horizontal

    @alignment_horizontal.setter
    def alignment_horizontal(self, value):
        if value not in ("left", "center", "right"):
            raise ValueError("AlignmentHorizontal should be one of 'left', 'center', 'right'. Got: {}".format(value))
        self._alignment_horizontal = value

    @property
    def alignment_multiline(self):
        return self._alignment_multiline

    @alignment_multiline.setter
    def alignment_multiline(self, value):
        if value not in ("left", "center", "right"):
            raise ValueError("AlignmentMultiline should be one of 'left', 'center', 'right'. Got: {}".format(value))
        self._alignment_multiline = value

    @property
    def stacked_marking(self):
        return self._stacked_marking

    @stacked_marking.setter
    def stacked_marking(self, value):
        if value not in (True, False):
            raise ValueError("StackedMarking should be a Boolean. Got: {}".format(value))
        self._stacked_marking = value

    @property
    def text_height_auto(self):
        return self._text_height_auto

    @text_height_auto.setter
    def text_height_auto(self, value):
        if value not in (True, False):
            raise ValueError("TextHeightAuto should be a Boolean. Got: {}".format(value))
        self._text_height_auto = value

    @property
    def text_height(self):
        return self._text_height

    @text_height.setter
    def text_height(self, value):
        if 0 <= value <= 50000:
            self._text_height = value
        else:
            raise ValueError("TextHeight should be between 0 and 50000. Got: {}".format(value))

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        if value == "":
            raise ValueError("Text should not be empty.")
        self._text = value


    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, _):
        """Apply the feature to the beam geometry.

        Raises
        -------

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing. #TODO: think about ways to display text curves from `draw_string_on_element()`

        """
        # NOTE: this currently does nothing due to the fact the visualizing the text as a brep subtraction is very heavy and usually unnecessary.
        return geometry

    def create_text_curves_for_element(self, element):
        """This returns translated and scaled curves which correspond to the text and the element the text is engraved on.

        Parameters
        ----------
        element : :class:`compas_timber.elements.Beam`
            The beam on which the text is engraved.

        Returns
        -------
        list[:class:`compas.geometry.Curve`]
            The curves representing the text.
        """
        assert self.text
        assert self.text_height is not None
        assert self.start_x is not None
        assert self.start_y is not None

        self._load_character_dict()

        ref_side_index = self.ref_side_index or 0
        face = element.ref_sides[ref_side_index]
        string_curves = []
        x_pos = 0
        spacing = 0.1
        for char in self.text:
            curves = Text._CHARACTER_DICT[char]["curves"]
            translated_crvs = []
            for crv in curves:
                translated_crvs.append(crv.translated([x_pos + spacing,0,0]))
            string_curves.extend(translated_crvs)
            x_pos += spacing + Text._CHARACTER_DICT[char]["width"]
        x_pos *= self.text_height

        if self.alignment_vertical == AlignmentType.BOTTOM:
            y_offset = 0
        elif self.alignment_vertical == AlignmentType.CENTER:
            y_offset = -self.text_height / 2
        elif self.alignment_vertical == AlignmentType.TOP:
            y_offset = -self.text_height

        if self.alignment_horizontal == AlignmentType.LEFT:
            x_offset = 0
        elif self.alignment_horizontal == AlignmentType.CENTER:
            x_offset = -x_pos / 2
        elif self.alignment_horizontal == AlignmentType.RIGHT:
            x_offset = -x_pos


        for crv in string_curves:
            for pt in crv.points:
                pt.transform(Scale.from_factors([self.text_height]*3))
                pt.translate([self.start_x+x_offset, self.start_y+y_offset, 0])
                pt.transform(Transformation.from_frame_to_frame(Frame.worldXY(), face))
        return string_curves


class TextParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(TextParams, self).__init__(instance)

    def as_dict(self):
        result = OrderedDict()
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["AlignmentVertical"] = self._instance.alignment_vertical
        result["AlignmentHorizontal"] = self._instance.alignment_horizontal
        result["AlignmentMultiline"] = self._instance.alignment_multiline
        result["StackedMarking"] = "yes" if self._instance.stacked_marking else "no"
        result["TextHeightAuto"] = "yes" if self._instance.text_height_auto else "no"
        result["TextHeight"] = "{:.{prec}f}".format(float(self._instance.text_height), prec=TOL.precision)
        result["Text"] = self._instance.text
        return result
