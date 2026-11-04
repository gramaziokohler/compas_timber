import xml.etree.ElementTree as ET

from compas.data import Data
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_brep import Brep
from compas_brep import NurbsSurface

from .btlx import AttributeSpec
from .btlx import BTLxWriter
from .btlx import ParametricProcessing


def _knots_and_mults(knots, count, degree):
    # the figure of the BTLx manual lists count + degree - 1 knots, the schema says count + degree, a surface needs count + degree + 1
    while len(knots) < count + degree + 1:
        knots = knots[:1] + knots if knots.count(knots[0]) <= knots.count(knots[-1]) else knots + knots[-1:]
    unique = sorted(set(knots))
    return unique, [knots.count(knot) for knot in unique]


class NurbsPatch(Data):
    """A NURBS surface as it is defined in BTLx.

    Parameters
    ----------
    points : list(:class:`~compas.geometry.Point`)
        The control points, in the coordinates of the reference side.
        The list is organized row wise: `count_v` rows of `count_u` points, which is P(U=0, V=0), P(U=1, V=0), ..., P(U=0, V=1), ...
    weights : list(float)
        The weights of the control points.
    knots_u : list(float)
        The knots in the direction of U, with their multiplicity and without the first and last one of a full knot vector.
    knots_v : list(float)
        The knots in the direction of V, as `knots_u`.
    degree_u : int
        The degree in the direction of U.
    degree_v : int
        The degree in the direction of V.
    count_u : int
        The number of control points in the direction of U.
    count_v : int
        The number of control points in the direction of V.

    """

    @property
    def __data__(self):
        return {
            "points": self.points,
            "weights": self.weights,
            "knots_u": self.knots_u,
            "knots_v": self.knots_v,
            "degree_u": self.degree_u,
            "degree_v": self.degree_v,
            "count_u": self.count_u,
            "count_v": self.count_v,
        }

    def __init__(self, points, weights, knots_u, knots_v, degree_u, degree_v, count_u, count_v):
        super(NurbsPatch, self).__init__()
        if not len(points) == len(weights) == count_u * count_v:
            raise ValueError("A patch of {} by {} needs as many control points and weights. Got: {}, {}".format(count_u, count_v, len(points), len(weights)))
        self.points = [Point(*point) for point in points]
        self.weights = weights
        self.knots_u = knots_u
        self.knots_v = knots_v
        self.degree_u = degree_u
        self.degree_v = degree_v
        self.count_u = count_u
        self.count_v = count_v

    def scale(self, factor):
        self.points = [point * factor for point in self.points]

    def to_surface(self):
        """Converts this patch to a surface.

        Returns
        -------
        :class:`~compas_brep.NurbsSurface`

        """

        def grid(values):
            return [[values[v * self.count_u + u] for v in range(self.count_v)] for u in range(self.count_u)]

        knots_u, mults_u = _knots_and_mults(self.knots_u, self.count_u, self.degree_u)
        knots_v, mults_v = _knots_and_mults(self.knots_v, self.count_v, self.degree_v)
        return NurbsSurface.from_parameters(grid(self.points), grid(self.weights), knots_u, knots_v, mults_u, mults_v, self.degree_u, self.degree_v)

    @classmethod
    def from_surface(cls, surface):
        """Creates a patch from a surface.

        Parameters
        ----------
        surface : :class:`~compas_brep.NurbsSurface`
            The surface.

        Returns
        -------
        :class:`NurbsPatch`

        """
        count_u, count_v = len(surface.points), len(surface.points[0])
        points = [surface.points[u][v] for v in range(count_v) for u in range(count_u)]
        weights = [surface.weights[u][v] for v in range(count_v) for u in range(count_u)]
        return cls(points, weights, surface.knotvector_u[1:-1], surface.knotvector_v[1:-1], surface.degree_u, surface.degree_v, count_u, count_v)

    @classmethod
    def from_xml(cls, element):
        """Creates a patch from the XML element which holds it.

        Parameters
        ----------
        element : :class:`~xml.etree.ElementTree.Element`
            The `Surface` element.

        Returns
        -------
        :class:`NurbsPatch`

        """
        control_points = element.findall("{*}ControlPoints/{*}ControlPoint")
        return cls(
            [[float(point.attrib[axis]) for axis in "XYZ"] for point in control_points],
            [float(point.attrib["W"]) for point in control_points],
            [float(knot) for knot in element.find("{*}KnotsU").text.split()],
            [float(knot) for knot in element.find("{*}KnotsV").text.split()],
            int(element.attrib["DegreeU"]),
            int(element.attrib["DegreeV"]),
            int(element.attrib["CountU"]),
            int(element.attrib["CountV"]),
        )


def nurbs_patch_to_xml(patch):
    """Converts a patch to an XML element.

    Parameters
    ----------
    patch : :class:`NurbsPatch`
        The patch to be converted.

    Returns
    -------
    :class:`~xml.etree.ElementTree.Element`
        The element which represents the patch.

    """
    root = ET.Element("Surface", {"DegreeU": str(patch.degree_u), "DegreeV": str(patch.degree_v), "CountU": str(patch.count_u), "CountV": str(patch.count_v)})
    control_points = ET.SubElement(root, "ControlPoints")
    for point, weight in zip(patch.points, patch.weights):
        attributes = {axis: "{:.{prec}f}".format(value, prec=BTLxWriter.POINT_PRECISION) for axis, value in zip("XYZ", point)}
        ET.SubElement(control_points, "ControlPoint", dict(attributes, W=str(float(weight))))
    ET.SubElement(root, "KnotsU").text = " ".join(str(float(knot)) for knot in patch.knots_u)
    ET.SubElement(root, "KnotsV").text = " ".join(str(float(knot)) for knot in patch.knots_v)
    return root


BTLxWriter.register_type_serializer(NurbsPatch.__name__, nurbs_patch_to_xml)


class FreeSurface(ParametricProcessing):
    """Represents a free NURBS surface. The material on the side of the machining, towards the reference side, is removed up to the surface.

    Parameters
    ----------
    surface : :class:`NurbsPatch`
        The surface.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "FreeSurface"  # type: ignore
    ATTRIBUTE_MAP = {"Surface": AttributeSpec("surface", NurbsPatch)}

    def scale(self, factor):
        """Scale the control points of this processing.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        self.surface.scale(factor)

    @classmethod
    def from_surface_and_element(cls, surface, element, ref_side_index=0, **kwargs):
        """Construct this processing from a surface and an element.

        Parameters
        ----------
        surface : :class:`~compas_brep.NurbsSurface`
            The surface, in model coordinates.
        element : :class:`~compas_timber.base.TimberElement`
            The element.
        ref_side_index : int, optional
            The reference side. The removed material is between the surface and this side.
        **kwargs : dict, optional
            The keyword arguments of this processing.

        Returns
        -------
        :class:`FreeSurface`

        """
        surface = surface.transformed(Transformation.from_frame(element.ref_sides[ref_side_index]).inverse())
        return cls(surface=NurbsPatch.from_surface(surface), ref_side_index=ref_side_index, **kwargs)

    @classmethod
    def from_shapes_and_element(cls, surface, element, **kwargs):
        """Construct this processing from a surface and an element, see :meth:`from_surface_and_element`."""
        return cls.from_surface_and_element(surface, element, **kwargs)

    def volumes_from_params_and_element(self, element):
        """The volume between the surface and the reference side, within the outline of the surface.

        The figure shows the machining above and the material below a surface which has U and V in the direction of X and Y of the view on the reference side.
        It does not say if a surface with the opposite orientation flips this, so the machining is always on the side of the reference side.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        height = max(element.width, element.height, element.blank_length) + max(abs(point.z) for point in self.surface.points)
        try:
            volume = Brep.from_extrusion(Brep.from_surface(self.surface.to_surface()).faces[0], Vector(0.0, 0.0, height))
        except TypeError as ex:
            # shortcut: the Rhino backend of compas_brep extrudes curves only, upgrade when it extrudes a face
            raise ValueError("The surface cannot be extruded: {}".format(ex))
        return [volume.transformed(Transformation.from_frame(element.ref_sides[self.ref_side_index]))]
