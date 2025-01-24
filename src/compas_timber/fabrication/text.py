import os

from compas.data import json_load
from compas.geometry import Transformation
from compas.geometry import Scale
from compas.geometry import Frame

from compas.tolerance import TOL

import compas_timber

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams

class Text(BTLxProcessing):
    """Represents a drilling processing.

    Parameters
    ----------
    start_x : float
        The x-coordinate of the start point of the drilling. In the local coordinate system of the reference side.
    start_y : float
        The y-coordinate of the start point of the drilling. In the local coordinate system of the reference side.
    angle : float
        The rotation angle of the drilling. In degrees. Around the z-axis of the reference side.
    inclination : float
        The inclination angle of the drilling. In degrees. Around the y-axis of the reference side.
    depth_limited : bool, default True
        If True, the drilling depth is limited to `depth`. Otherwise, drilling will go through the element.
    depth : float, default 50.0
        The depth of the drilling. In mm.
    diameter : float, default 20.0
        The diameter of the drilling. In mm.

StartX LengthPosType 0 -100000 100000
StartY WidthNType 0 -50000 50000
Angle Angle2NType 0 -180 180
AlignmentVertical AlignmentVerticalType bottom
AlignmentHorizontal AlignmentHorizontalType left
AlignmentMultiline AlignmentHorizontalType left
StackedMarking BooleanType no no yes
TextHeightAuto BooleanType yes no yes
TextHeight WidthType 20 0 50000
Text xs:string
    """

    # TODO: add __data__

    PROCESSING_NAME = "Text"  # type: ignore

    def __init__(self, start_x=0.0, start_y=0.0, angle=0.0, alignment_vertical="bottom", alignment_horizontal="left", alignment_multiline="left", stacked_marking=False, text_height_auto=True, text_height=20.0, text="", **kwargs):
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
        for crv in string_curves:
            for pt in crv.points:
                pt.transform(Scale.from_factors([self.text_height]*3))
                pt.translate([self.start_x, self.start_y, 0])
                pt.transform(Transformation.from_frame_to_frame(Frame.worldXY(), face))
        return string_curves

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


