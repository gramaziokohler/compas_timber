import xml.etree.ElementTree as ET

from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.errors import BTLxParsingError

from .btlx import AttributeSpec
from .btlx import BTLxWriter
from .btlx import ParametricProcessing
from .containers import frame_to_xml


class InsertionPattern(Data):
    """A processing which is placed at each node of a :class:`PatternContour`.

    Parameters
    ----------
    processing : :class:`~compas_timber.fabrication.BTLxProcessing`
        The processing. Its parameters refer to `position`, its reference side is ignored.
    position : :class:`~compas.geometry.Frame`
        The position of the processing in the local coordinate system of a node.

    """

    @property
    def __data__(self):
        return {"processing": self.processing, "position": self.position}

    def __init__(self, processing, position=None):
        super(InsertionPattern, self).__init__()
        self.processing = processing
        self.position = position or Frame.worldXY()


class InsertionPatterns(Data):
    """The processings placed at each node of a :class:`PatternContour`.

    Parameters
    ----------
    patterns : list(:class:`InsertionPattern`)
        The patterns. The BTLx schema requires at least one.

    """

    @property
    def __data__(self):
        return {"patterns": self.patterns}

    def __init__(self, patterns):
        super(InsertionPatterns, self).__init__()
        self.patterns = patterns

    def scale(self, factor):
        for pattern in self.patterns:
            pattern.processing.scale(factor)
            pattern.position = Frame(pattern.position.point * factor, pattern.position.xaxis, pattern.position.yaxis)


def insertion_patterns_to_xml(insertion_patterns):
    root = ET.Element("InsertionPatterns")
    for pattern in insertion_patterns.patterns:
        element = ET.SubElement(root, "InsertionPattern")
        element.append(BTLxWriter._processing_to_element(pattern.processing))
        element.append(frame_to_xml(pattern.position))
    return root


class NodeContourSegment(Data):
    """A straight segment of a :class:`NodeContour`.

    Parameters
    ----------
    end_point : :class:`~compas.geometry.Point`
        The end of the segment, in the coordinates of the reference side.
    node_spacing : float, optional
        The distance between the nodes along the segment. 0 means no nodes between its ends.
    node_at_start : bool, optional
        True if the start of the segment is a node.
    node_at_end : bool, optional
        True if the end of the segment is a node.

    """

    @property
    def __data__(self):
        return {"end_point": self.end_point, "node_spacing": self.node_spacing, "node_at_start": self.node_at_start, "node_at_end": self.node_at_end}

    def __init__(self, end_point, node_spacing=0.0, node_at_start=True, node_at_end=True):
        super(NodeContourSegment, self).__init__()
        self.end_point = Point(*end_point)
        self.node_spacing = node_spacing
        self.node_at_start = node_at_start
        self.node_at_end = node_at_end


class NodeContour(Data):
    """The contour of a :class:`PatternContour`.

    Parameters
    ----------
    start_point : :class:`~compas.geometry.Point`
        The start of the contour, in the coordinates of the reference side.
    segments : list(:class:`NodeContourSegment`)
        The segments of the contour.

    """

    @property
    def __data__(self):
        return {"start_point": self.start_point, "segments": self.segments}

    def __init__(self, start_point, segments):
        super(NodeContour, self).__init__()
        self.start_point = Point(*start_point)
        self.segments = segments

    def scale(self, factor):
        self.start_point = self.start_point * factor
        for segment in self.segments:
            segment.end_point = segment.end_point * factor
            segment.node_spacing *= factor

    def node_frames(self):
        """The local coordinate systems of the nodes, in the coordinates of the reference side.

        The X axis of a node points to the start of its segment. Its Y axis lies in the plane of the contour, perpendicular to X.
        A node shared by two segments belongs to the first one.

        Returns
        -------
        list(:class:`~compas.geometry.Frame`)

        """
        frames = []
        start = self.start_point
        for segment in self.segments:
            direction = Vector.from_start_end(start, segment.end_point)
            length = direction.length
            xaxis = direction * (-1.0 / length)
            yaxis = Vector(0.0, 0.0, 1.0).cross(xaxis)

            # the last space of a segment is shorter if its length is not a multiple of the spacing
            distances = [segment.node_spacing * i for i in range(1, int(length / segment.node_spacing) + 1)] if segment.node_spacing else []
            distances = [distance for distance in distances if distance < length and not TOL.is_close(distance, length)]
            if segment.node_at_start:
                distances.insert(0, 0.0)
            if segment.node_at_end:
                distances.append(length)

            for distance in distances:
                point = start + direction * (distance / length)
                if not any(TOL.is_allclose(point, frame.point) for frame in frames):
                    frames.append(Frame(point, xaxis, yaxis))
            start = segment.end_point
        return frames

    @classmethod
    def from_xml(cls, element):
        if element.find("{*}Arc") is not None:
            # shortcut: straight segments only, as with Contour, upgrade when arcs are needed by a real file
            raise BTLxParsingError("PatternContour with arc segments is not supported.", processing_type="PatternContour")
        start_point = [float(element.find("{*}StartPoint").attrib[axis]) for axis in "XYZ"]
        segments = []
        for line in element.findall("{*}Line"):
            end_point = line.find("{*}EndPoint")
            segments.append(
                NodeContourSegment(
                    [float(end_point.attrib[axis]) for axis in "XYZ"],
                    float(line.attrib.get("NodeSpacing", 0.0)),
                    line.attrib.get("NodeAtStart", "yes") == "yes",
                    line.attrib.get("NodeAtEnd", "yes") == "yes",
                )
            )
        return cls(start_point, segments)


def _point_attributes(point):
    return {axis: "{:.{prec}f}".format(value, prec=BTLxWriter.POINT_PRECISION) for axis, value in zip("XYZ", point)}


def node_contour_to_xml(contour):
    root = ET.Element("Contour")
    ET.SubElement(root, "StartPoint", _point_attributes(contour.start_point))
    for segment in contour.segments:
        attributes = {
            "NodeSpacing": "{:.{prec}f}".format(segment.node_spacing, prec=BTLxWriter.POINT_PRECISION),
            "NodeAtStart": "yes" if segment.node_at_start else "no",
            "NodeAtEnd": "yes" if segment.node_at_end else "no",
        }
        ET.SubElement(ET.SubElement(root, "Line", attributes), "EndPoint", _point_attributes(segment.end_point))
    return root


class PatternContour(ParametricProcessing):
    """A list of processings which is repeated at each node of a contour.

    The parameters of a processing refer to its position, the position refers to a node, and the node refers to the contour.

    Parameters
    ----------
    insertion_patterns : :class:`InsertionPatterns`
        The processings to repeat, with their position relative to a node.
    contour : :class:`NodeContour`
        The contour which defines the nodes.

    """

    PROCESSING_NAME = "PatternContour"  # type: ignore
    ATTRIBUTE_MAP = {
        "InsertionPatterns": AttributeSpec("insertion_patterns", InsertionPatterns),
        "Contour": AttributeSpec("contour", NodeContour),
    }

    def scale(self, factor):
        super(PatternContour, self).scale(factor)
        self.insertion_patterns.scale(factor)
        self.contour.scale(factor)

    def apply(self, geometry, element):
        """Apply the processings of the insertion patterns at each node of the contour.

        A processing is defined on a reference side of the element, so instead of moving the processing to a node,
        the element is moved such that the node's position lands on the reference side, and moved back afterwards.
        This works for any processing, but those which depend on the element's dimensions see the unmoved element.

        Parameters
        ----------
        geometry : :class:`~compas_brep.Brep`
            The element's geometry, in the element's local coordinates.
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        :class:`~compas_brep.Brep`
            The resulting geometry.

        """
        ref_side = element.transformation_to_local() * Transformation.from_frame(element.ref_sides[self.ref_side_index])
        for node in self.contour.node_frames():
            for pattern in self.insertion_patterns.patterns:
                processing = pattern.processing.copy()
                processing.ref_side_index = self.ref_side_index
                placement = ref_side * Transformation.from_frame(node) * Transformation.from_frame(pattern.position) * ref_side.inverted()
                geometry = processing.apply(geometry.transformed(placement.inverted()), element).transformed(placement)
        return geometry


BTLxWriter.register_type_serializer(InsertionPatterns.__name__, insertion_patterns_to_xml)
BTLxWriter.register_type_serializer(NodeContour.__name__, node_contour_to_xml)
