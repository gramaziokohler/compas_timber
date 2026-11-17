import xml.etree.ElementTree as ET

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from .btlx import AttributeSpec
from .btlx import BTLxWriter
from .btlx import OrientationType
from .btlx import ParametricProcessing


def frame_to_xml(frame, tag="Position"):
    """Converts a frame to an element of the BTLx `CoordinateSystemType`.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The frame.
    tag : str, optional
        The name of the element.

    Returns
    -------
    :class:`~xml.etree.ElementTree.Element`

    """
    root = ET.Element(tag)
    for name, coordinates in (("ReferencePoint", frame.point), ("XVector", frame.xaxis), ("YVector", frame.yaxis)):
        ET.SubElement(root, name, {axis: str(float(value)) for axis, value in zip("XYZ", coordinates)})
    return root


def frame_from_xml(element):
    """Converts an element of the BTLx `CoordinateSystemType` to a frame.

    Parameters
    ----------
    element : :class:`~xml.etree.ElementTree.Element`
        The element.

    Returns
    -------
    :class:`~compas.geometry.Frame`

    """
    point, xaxis, yaxis = [[float(element.find("{*}" + name).attrib[axis]) for axis in "XYZ"] for name in ("ReferencePoint", "XVector", "YVector")]
    return Frame(Point(*point), Vector(*xaxis), Vector(*yaxis))


class ProcessingParameter(Data):
    """A named parameter of a processing, whose meaning is defined by the receiver of the BTLx file.

    Parameters
    ----------
    name : str
        The name of the parameter.
    value : float or str, optional
        The value of the parameter.

    """

    @property
    def __data__(self):
        return {"name": self.name, "value": self.value}

    def __init__(self, name, value=None):
        super(ProcessingParameter, self).__init__(name=name)
        self.value = value

    def scale(self, factor):
        """Scale the value, which the BTLx schema defines as a length, if it is a number."""
        if isinstance(self.value, (int, float)):
            self.value *= factor

    def to_xml(self, tag):
        root = ET.Element(tag, {"Name": self.name})
        if isinstance(self.value, str):
            ET.SubElement(root, "StringValue").text = self.value
        elif self.value is not None:
            ET.SubElement(root, "Value").text = "{:.{prec}f}".format(self.value, prec=BTLxWriter.POINT_PRECISION)
        return root

    @classmethod
    def from_xml(cls, element):
        value = element.find("{*}Value")
        string_value = element.find("{*}StringValue")
        if value is not None:
            return cls(element.attrib["Name"], float(value.text))
        return cls(element.attrib["Name"], string_value.text if string_value is not None else None)


class VariantParameter(ProcessingParameter):
    """A parameter of a :class:`Variant`."""


class ConnectorParameter(ProcessingParameter):
    """A parameter of a :class:`ConnectorInfo`."""


class ConnectorInfo(Data):
    """The description of a connector.

    Parameters
    ----------
    connector_type : str
        The type of the connector, known to the receiver of the BTLx file.
    position : :class:`~compas.geometry.Frame`
        The position of the connector.
    parameters : list(:class:`ConnectorParameter`), optional
        Additional parameters of the connector, e.g. its depth.

    """

    @property
    def __data__(self):
        return {"connector_type": self.connector_type, "position": self.position, "parameters": self.parameters}

    def __init__(self, connector_type, position, parameters=None):
        super(ConnectorInfo, self).__init__()
        self.connector_type = connector_type
        self.position = position
        self.parameters = parameters or []

    def scale(self, factor):
        self.position = Frame(self.position.point * factor, self.position.xaxis, self.position.yaxis)
        for parameter in self.parameters:
            parameter.scale(factor)

    @classmethod
    def from_xml(cls, element):
        return cls(
            element.find("{*}Type").text,
            frame_from_xml(element.find("{*}Position")),
            [ConnectorParameter.from_xml(parameter) for parameter in element.findall("{*}ConnectorParameter")],
        )


def connector_info_to_xml(info):
    root = ET.Element("ConnectorInfo")
    ET.SubElement(root, "Type").text = info.connector_type
    root.append(frame_to_xml(info.position))
    root.extend(parameter.to_xml("ConnectorParameter") for parameter in info.parameters)
    return root


class ProcessingGroup(ParametricProcessing):
    """A group of processings, which are given as `subprocessings`.

    Parameters
    ----------
    subprocessings : list(:class:`~compas_timber.fabrication.BTLxProcessing`)
        The processings in this group. The BTLx schema requires at least one.

    """

    PROCESSING_NAME = "ProcessingGroup"  # type: ignore
    ATTRIBUTE_MAP = {}
    WRAPS_SUBPROCESSINGS = True


class Connector(ParametricProcessing):
    """A connector, optionally with the processings it needs, which are given as `subprocessings`.

    A receiver which knows the connector's type may produce it with its own tools, otherwise it produces the `subprocessings`.
    The geometry of the element is the result of the `subprocessings`.

    Parameters
    ----------
    connector_info : :class:`ConnectorInfo`
        The description of the connector.
    subprocessings : list(:class:`~compas_timber.fabrication.BTLxProcessing`), optional
        The processings which produce the connector.

    """

    PROCESSING_NAME = "Connector"  # type: ignore
    ATTRIBUTE_MAP = {"ConnectorInfo": AttributeSpec("connector_info", ConnectorInfo)}
    WRAPS_SUBPROCESSINGS = True

    def scale(self, factor):
        super(Connector, self).scale(factor)
        self.connector_info.scale(factor)


class Variant(ParametricProcessing):
    """A processing which is defined by the receiver of the BTLx file, which makes it a named set of parameters.

    It has no geometric meaning in the BTLx specification, so it leaves the element's geometry as it is.

    Parameters
    ----------
    orientation : str, optional
        Either OrientationType.START or OrientationType.END.
    cut_off : bool, optional
        True if the element is cut off at the position of the variant.
    start_x : float, optional
        The position along the reference side.
    start_y : float, optional
        The position across the reference side.
    start_depth : float, optional
        The position below the reference side.
    parameters : list(:class:`VariantParameter`), optional
        The parameters of the variant.

    """

    PROCESSING_NAME = "Variant"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, choices=(OrientationType.START, OrientationType.END)),
        "CutOff": AttributeSpec("cut_off", bool, False),
        "StartX": AttributeSpec("start_x", float, None, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, None, (-100000.0, 100000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, None, (-100000.0, 100000.0), scales=True),
        "VariantParameter": AttributeSpec("parameters", VariantParameter, multiple=True),
    }

    def scale(self, factor):
        super(Variant, self).scale(factor)
        for parameter in self.parameters or []:
            parameter.scale(factor)


BTLxWriter.register_type_serializer(ConnectorInfo.__name__, connector_info_to_xml)
BTLxWriter.register_type_serializer(VariantParameter.__name__, lambda parameter: parameter.to_xml("VariantParameter"))
