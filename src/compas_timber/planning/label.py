from compas.data import Data

from compas_timber.fabrication import AlignmentType
from compas_timber.fabrication import Text


class Label(object):
    """A label for a timber assembly.

    Attributes
    ----------
    element : :class:`compas_timber.structure.Beam`
        The element to which the label is attached.
    text : str
        The text of the label.
    """

    def __init__(self, element, text=None):
        self.element = element
        self.text = (
            text
            if text
            else "{}_{}_{}".format(self.element.__class__.__name__, self.element.key, self.element.attributes.get("category") if self.element.attributes.get("category") else "")
        )

    @property
    def __data__(self):
        return {"element": self.element, "text": self.text}

    @classmethod
    def from_element(cls, element, attributes=[], base_string="", char_to_replace=None):
        """Get text from attributes of the element.

        Parameters
        ----------
        element : :class:`compas_timber.structure.Beam`
            The element to which the label is attached.
        attributes : list
            List of element's attributes to be included in the label.
        base_string : str
            Base string to be used for the label.
        char_to_replace : str
            Character to be replaced in the base string.

        Returns
        -------
        :class:`compas_timber.planning.Label`
            The label object.

        """

        string_out = ""
        att_names = [a for a in attributes] if attributes else []
        for char in base_string:
            if char != char_to_replace:
                string_out += char
            else:
                string_out += str(getattr(element, att_names.pop(0), " ") if len(att_names) > 0 else "_")
        for attribute in att_names:
            string_out += str(getattr(element, attribute, " "))
            string_out += "-"
        return cls(element, string_out)

    def engrave_on_beam(self, beam, text_height=None, ref_side_index=0):
        """Create the Text BTLxProcessing to engrave the label on a beam.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam to engrave the label on.
        text_height : float
            The height of the text.
        ref_side_index : int
            The reference side index.

        Returns
        -------
        :class:`compas_timber.fabrication.Text`
            The Text BTLxProcessing object.


        """
        text_height = text_height if text_height else min(beam.width, beam.height) / 2
        x_positions = [0.0, beam.length]
        for feat in beam.features:
            if getattr(feat, "start_x", None):
                x_positions.append(feat.start_x)
        if x_positions:
            x_positions.sort()
            biggest_gap = (0, 0)
        for i in range(len(x_positions) - 1):
            if x_positions[i + 1] - x_positions[i] > biggest_gap[1] - biggest_gap[0]:
                biggest_gap = (x_positions[i], x_positions[i + 1])
        x_pos = (biggest_gap[0] + biggest_gap[1]) / 2
        return Text(
            ref_side_index = ref_side_index,
            start_x=x_pos,
            start_y=self.element.side_as_surface(ref_side_index).ysize / 2.0,
            alignment_horizontal=AlignmentType.CENTER,
            alignment_vertical=AlignmentType.CENTER,
            text_height=text_height,
            text=self.text,
        )


class DeferredLabel(Data):
    """A deferred label for a timber assembly, allowing attribues generated via joinery and other processings to be included in label data.

    parameters
    ----------
    elements : list
        The elements to which the label is attached.
    base_string : str
        The base string of the label.
    attributes : list
        List of element's attributes to be included in the label.
    char_to_replace : str
        Character to be replaced in the base string.
    text_height : float
        The height of the text.
    ref_side_index : int
        The reference side index.


    """

    def __init__(self, elements, base_string=None, attributes=None, char_to_replace=None, text_height=None, ref_side_index=0):
        self.elements = elements
        self.base_string = base_string
        self.attributes = attributes
        self.char_to_replace = char_to_replace
        self.text_height = text_height
        self.ref_side_index = ref_side_index

    def __str__(self):
        return "DeferredLabel: {}".format(self.base_string)

    @property
    def __data__(self):
        return {
            "elements": self.elements,
            "attributes": self.attributes,
            "base_string": self.base_string,
            "char_to_replace": self.char_to_replace,
            "text_height": self.text_height,
        }

    def feature_from_element(self, element):
        """Get the Text BTLxProcessing object to apply to the element."""

        if not element.is_beam:
            raise NotImplementedError("Engraving for {} not implemented".format(element.__class__.__name__))
        label = Label.from_element(element, self.attributes, self.base_string, self.char_to_replace)  # get Label object.
        return label.engrave_on_beam(element, self.text_height, self.ref_side_index)  # return Text processing object.
