import os

from compas.data import json_load
from compas.geometry import Transformation
from compas.geometry import Scale
from compas.geometry import Frame
from compas.tolerance import TOL


from .btlx import AlignmentType
from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams


class Text(BTLxProcessing):
    """Represents a Text feature to be made on a beam.

    Parameters
    ----------
    start_x : float
        The start x-coordinate of the cut in parametric space of the reference side. -100000.0 < start_x < 100000.0.
    start_y : float
        The start y-coordinate of the cut in parametric space of the reference side. 0.0 < start_y < 50000.0.
    angle : float
        The horizontal angle of the first cut. -179.9 < angle < 179.9.
    alignment_vertical : int
        The vertical alignment of the text. Should be either AlignmentType.TOP, AlignmentType.CENTER ot AlignmentType.BOTTOM.
    alignment_horizontal : int
        The horizontal alignment of the text. Should be either AlignmentType.LEFT, AlignmentType.CENTER or AlignmentType.RIGHT.
    alignment_multiline : int
        The alignment of the text in multiline mode. Should be either AlignmentType.LEFT, AlignmentType.CENTER or AlignmentType.RIGHT.
    stacked_marking : bool
        If the text is a stacked marking.
    text_height_auto : bool
        If the text height is automatically calculated.
    text_height : float
        The height of the text. 0.1 < text_height < 5000.0.
    text : str
        The text to be engraved on the beam.

    """

    PROCESSING_NAME = "Text"  # type: ignore

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
        start_x=0.0,
        start_y=0.0,
        angle=0.0,
        alignment_vertical=AlignmentType.BOTTOM,
        alignment_horizontal=AlignmentType.LEFT,
        alignment_multiline=AlignmentType.LEFT,
        stacked_marking=False,
        text_height_auto=True,
        text_height=20.0,
        text="",
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


    ########################################################################
    # Properties
    ########################################################################

    @property
    def params_dict(self):
        return TextParams(self).as_dict()

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
        if value not in ["bottom", "center", "top"]:
            raise ValueError("AlignmentVertical should be one of 'bottom', 'center', 'top'. Got: {}".format(value))
        self._alignment_vertical = value

    @property
    def alignment_horizontal(self):
        return self._alignment_horizontal

    @alignment_horizontal.setter
    def alignment_horizontal(self, value):
        if value not in ["left", "center", "right"]:
            raise ValueError("AlignmentHorizontal should be one of 'left', 'center', 'right'. Got: {}".format(value))
        self._alignment_horizontal = value

    @property
    def alignment_multiline(self):
        return self._alignment_multiline

    @alignment_multiline.setter
    def alignment_multiline(self, value):
        if value not in ["left", "center", "right"]:
            raise ValueError("AlignmentMultiline should be one of 'left', 'center', 'right'. Got: {}".format(value))
        self._alignment_multiline = value

    @property
    def stacked_marking(self):
        return self._stacked_marking

    @stacked_marking.setter
    def stacked_marking(self, value):
        if value not in [True, False]:
            raise ValueError("StackedMarking should be a Boolean. Got: {}".format(value))
        self._stacked_marking = value

    @property
    def text_height_auto(self):
        return self._text_height_auto

    @text_height_auto.setter
    def text_height_auto(self, value):
        if value not in [True, False]:
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
        self._text = value


    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Raises
        -------

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing. #TODO: think about ways to display text curves from `draw_string_on_element()`

        """
        return [geometry]

    def draw_string_on_element(self, element):
        face = element.ref_sides[self.ref_side_index]

        character_dict = json_load(os.path.join(os.path.dirname(__file__), "basic_characters.json"))
        string_curves = []
        x_pos = 0
        spacing = 0.1
        for char in self.text:
            crvs = character_dict[char]["curves"]
            translated_crvs = []
            for crv in crvs:
                translated_crvs.append(crv.translated([x_pos+spacing,0,0]))
            string_curves.extend(translated_crvs)
            x_pos += spacing + character_dict[char]["width"]
        x_pos *= self.text_height

        if self.alignment_vertical == AlignmentType.BOTTOM:
            y_offset = 0
        elif self.alignment_vertical == AlignmentType.CENTER:
            y_offset = -self.text_height/2
        elif self.alignment_vertical == AlignmentType.TOP:
            y_offset = -self.text_height

        if self.alignment_horizontal == AlignmentType.LEFT:
            x_offset = 0
        elif self.alignment_horizontal == AlignmentType.CENTER:
            x_offset = -x_pos/2
        elif self.alignment_horizontal == AlignmentType.RIGHT:
            x_offset = -x_pos


        for crv in string_curves:
            for pt in crv.points:
                pt.transform(Scale.from_factors([self.text_height]*3))
                pt.translate([self.start_x+x_offset, self.start_y+y_offset, 0])
                pt.transform(Transformation.from_frame_to_frame(Frame.worldXY(), face))
        return string_curves

    @classmethod
    def label_element(cls, element, string = None, text_height = None):
        if element.is_beam:
            text_height = text_height if text_height else min(element.width, element.height) / 2
            x_positions = [0.0, element.length]
            for feat in element.features:
                if getattr(feat, "start_x", None):
                    x_positions.append(feat.start_x)
            if x_positions:
                x_positions.sort()
                biggest_gap = (0,0)
            for i in range(len(x_positions)-1):
                if x_positions[i+1] - x_positions[i] > biggest_gap[1]-biggest_gap[0]:
                    biggest_gap = (x_positions[i], x_positions[i+1])
            x_pos = (biggest_gap[0] + biggest_gap[1]) / 2
            string = string if string else "G{}_B{}".format(element.attributes["category"], element.key)
            text = cls( ref_side_index = 1, start_x=x_pos, start_y=text_height, alignment_horizontal = AlignmentType.CENTER, alignment_vertical = AlignmentType.CENTER, text_height = text_height, text = string)
            element.add_feature(text)
            return text
        else:
            raise ValueError("Only beams can be labeled.")


class TextParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(TextParams, self).__init__(instance)

    def as_dict(self):
        result = super(TextParams, self).as_dict()
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


