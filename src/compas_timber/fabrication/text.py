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
    def start_x(self, start_x):
        if start_x > 100000.0 or start_x < -100000.0:
            raise ValueError("Start X must be between -100000.0 and 100000.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0 or start_y < -50000.0:
            raise ValueError("Start Y must be between -50000.0 and 50000.")
        self._start_y = start_y

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < -179.9:
            raise ValueError("Angle must be between -179.9 and 179.9.")
        self._angle = angle

    @property
    def alignment_vertical(self):
        return self._alignment_vertical

    @alignment_vertical.setter
    def alignment_vertical(self, alignment_vertical):
        if alignment_vertical not in [AlignmentType.TOP, AlignmentType.CENTER, AlignmentType.BOTTOM]:
            raise ValueError("Vertical alignment must be one of AlignmentType.TOP, AlignmentType.CENTER or AlignmentType.BOTTOM.")
        self._alignment_vertical = alignment_vertical

    @property
    def alignment_horizontal(self):
        return self._alignment_horizontal

    @alignment_horizontal.setter
    def alignment_horizontal(self, alignment_horizontal):
        if alignment_horizontal not in [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT]:
            raise ValueError("Horizontal alignment must be one of AlignmentType.LEFT, AlignmentType.CENTER or AlignmentType.RIGHT.")
        self._alignment_horizontal = alignment_horizontal

    @property
    def alignment_multiline(self):
        return self._alignment_multiline

    @alignment_multiline.setter
    def alignment_multiline(self, alignment_multiline):
        if alignment_multiline not in [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT]:
            raise ValueError("Multiline alignment must be one of AlignmentType.LEFT, AlignmentType.CENTER or AlignmentType.RIGHT.")
        self._alignment_multiline = alignment_multiline

    @property
    def stacked_marking(self):
        return self._stacked_marking

    @stacked_marking.setter
    def stacked_marking(self, stacked_marking):
        if not isinstance(stacked_marking, bool):
            raise ValueError("Stacked marking must be a boolean.")
        self._stacked_marking = stacked_marking

    @property
    def text_height_auto(self):
        return self._text_height_auto

    @text_height_auto.setter
    def text_height_auto(self, text_height_auto):
        if not isinstance(text_height_auto, bool):
            raise ValueError("Text height auto must be a boolean.")
        self._text_height_auto = text_height_auto

    @property
    def text_height(self):
        return self._text_height

    @text_height.setter
    def text_height(self, text_height):
        if text_height > 5000.0 or text_height < 0.1:
            raise ValueError("Text height must be between 0.1 and 5000.")
        self._text_height = text_height

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        if not isinstance(text, str):
            raise ValueError("Text must be a string.")
        self._text = text

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_beam(cls, beam, start_x, text, stacked_marking=False, text_height=None, ref_side_index=0):
        """Create a Text instance from a beam.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam that is cut by this instance.
        start_x : float
            The start x-coordinate of the cut in parametric space of the reference side
        text : str
            The text to be engraved on the beam.
        stacked_marking : bool, optional
            If the text is a stacked marking. Default is False.
        text_height : float, optional
            The height of the text. Default is None.
        ref_side_index : int, optional
            The reference side index of the beam to be cut. Default is 0 (i.e. RS1).

        Returns
        -------
        :class:`~compas_timber.fabrication.Text`

        """
        # type: (Beam, float, str, bool, float, int) -> Text
        if not isinstance(text, str):
            text = str(text)

        ref_side = beam.side_as_surface(ref_side_index)

        start_y = ref_side.ysize/2
        angle = 0.0

        alignment_horizontal = AlignmentType.CENTER
        alignment_vertical = AlignmentType.CENTER
        alignment_multiline = AlignmentType.LEFT

        text_height_auto = True
        if text_height:
            text_height_auto = False

        return cls(
            start_x,
            start_y,
            angle,
            alignment_vertical,
            alignment_horizontal,
            alignment_multiline,
            stacked_marking,
            text_height_auto,
            text_height,
            text,
            ref_side_index=ref_side_index,
        )

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Parameters
        ----------
        geometry : :class:`~compas.geometry.Brep`
            The beam geometry to be cut.
        beam : :class:`compas_timber.elements.Beam`
            The beam that is cut by this instance.

        Raises
        ------
        :class:`~compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with beam geometry.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The resulting geometry after processing

        """
        # type: (Brep, Beam) -> Brep
        pass


class TextParams(BTLxProcessingParams):
    """A class to store the parameters of a Text feature.

    Parameters
    ----------
    instance : :class:`~compas_timber.fabrication.Text`
        The instance of the Text feature.
    """

    def __init__(self, instance):
        # type: (Text) -> None
        super(TextParams, self).__init__(instance)

    def as_dict(self):
        """Returns the parameters of the Text feature as a dictionary.

        Returns
        -------
        dict
            The parameters of the Text feature as a dictionary.
        """
        # type: () -> OrderedDict
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
        result["Text"] = str(self._instance.text)
        return result
