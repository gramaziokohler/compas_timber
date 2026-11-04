import re
import xml.etree.ElementTree as ET

from compas.data import Data
from compas.geometry import Transformation

from compas_timber.geometry import brep_difference_first
from compas_timber.geometry import brep_from_outlines

from .btlx import AttributeSpec
from .btlx import BTLxWriter
from .contours import ContourProcessing
from .contours import SimpleContour
from .contours import simple_contour_to_xml


class Apertures(Data):
    """The closed contours which are left out of an area.

    Parameters
    ----------
    contours : list(:class:`SimpleContour`)
        The contours, inside of the contour of the area. The BTLx schema requires at least one.

    """

    @property
    def __data__(self):
        return {"contours": self.contours}

    def __init__(self, contours):
        super(Apertures, self).__init__()
        self.contours = contours

    def scale(self, factor):
        for contour in self.contours:
            contour.scale(factor)

    @classmethod
    def from_xml(cls, element):
        return cls([SimpleContour.from_xml(aperture) for aperture in element.findall("{*}Aperture")])


def apertures_to_xml(apertures):
    root = ET.Element("Apertures")
    for contour in apertures.contours:
        root.append(simple_contour_to_xml(contour, "Aperture"))
    return root


BTLxWriter.register_type_serializer(Apertures.__name__, apertures_to_xml)


class AreaProcessing(ContourProcessing):
    """Base class for the processings which act on the area inside of a closed contour.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The closed contour of the area.
    apertures : :class:`Apertures`, optional
        The parts inside of `contour` which do not belong to the area.

    """

    ATTRIBUTE_MAP = {
        "Contour": AttributeSpec("contour", SimpleContour),
        "Apertures": AttributeSpec("apertures", Apertures),
    }
    MIN_POINTS = 4

    def __init__(self, **kwargs):
        super(AreaProcessing, self).__init__(**kwargs)
        if not self.contour.polyline.is_closed:
            raise ValueError("The contour of {} must be closed.".format(self.PROCESSING_NAME))

    def scale(self, factor):
        """Scale the lengths of this processing, of its contour and of its apertures.

        Parameters
        ----------
        factor : float
            The scaling factor.

        """
        super(AreaProcessing, self).scale(factor)
        if getattr(self, "apertures", None):  # a lockout area has none
            self.apertures.scale(factor)

    @classmethod
    def from_polyline_and_element(cls, polyline, element, ref_side_index=None, apertures=None, **kwargs):
        """Construct this processing from a polyline and an element.

        Parameters
        ----------
        polyline : :class:`~compas.geometry.Polyline`
            The closed contour of the area, in model coordinates.
        element : :class:`~compas_timber.base.TimberElement`
            The element.
        ref_side_index : int, optional
            The reference side. By default the one all points of `polyline` lie on.
        apertures : list(:class:`~compas.geometry.Polyline`), optional
            The closed contours of the apertures, in model coordinates.
        **kwargs : dict, optional
            The keyword arguments of this processing.

        Returns
        -------
        :class:`AreaProcessing`

        """
        if ref_side_index is None:
            ref_side_index = cls._ref_side_index_of_polyline(polyline, element)
        if apertures:
            to_ref_side = Transformation.from_frame(element.ref_sides[ref_side_index]).inverse()
            kwargs["apertures"] = Apertures([SimpleContour(aperture.transformed(to_ref_side)) for aperture in apertures])
        return super(AreaProcessing, cls).from_polyline_and_element(polyline, element, ref_side_index, **kwargs)


class GlueArea(AreaProcessing):
    """Represents an area where glue is applied. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The closed contour of the area.
    apertures : :class:`Apertures`, optional
        The parts of the area which stay free of glue.
    glue_type : str, optional
        The type of the glue.
    glue_amount : float, optional
        The amount of the glue. Greater than 0.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "GlueArea"  # type: ignore
    ATTRIBUTE_MAP = dict(
        AreaProcessing.ATTRIBUTE_MAP,
        GlueType=AttributeSpec("glue_type", str),
        GlueAmount=AttributeSpec("glue_amount", float),
    )

    @property
    def glue_amount(self):
        return self._glue_amount

    @glue_amount.setter
    def glue_amount(self, value):
        if value is not None and value <= 0.0:
            raise ValueError("glue_amount must be greater than 0. Got: {}".format(value))
        self._glue_amount = value


class PlaningArea(AreaProcessing):
    """Represents an area which is planed. It removes a layer of the given depth from the reference side.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The closed contour of the area.
    apertures : :class:`Apertures`, optional
        The parts of the area which are not planed.
    depth : float, optional
        The thickness of the removed layer, measured from the contour along -Z of the reference side. Without it, no material is removed.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "PlaningArea"  # type: ignore
    ATTRIBUTE_MAP = dict(AreaProcessing.ATTRIBUTE_MAP, Depth=AttributeSpec("depth", float, limits=(0.0, 1000.0), scales=True))

    def volumes_from_params_and_element(self, element):
        """The layer this processing removes from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        if not self.depth:
            return []
        polyline = self.contour.polyline
        # reaches past the reference side, so that the boolean leaves no sliver of it
        volume = brep_from_outlines(polyline.translated([0, 0, self.depth]), polyline.translated([0, 0, -self.depth]))
        for aperture in self.apertures.contours if self.apertures else []:
            volume = brep_difference_first(volume, brep_from_outlines(aperture.polyline.translated([0, 0, 2 * self.depth]), aperture.polyline.translated([0, 0, -2 * self.depth])))
        return [volume.transformed(Transformation.from_frame(element.ref_sides[self.ref_side_index]))]


class PlasterArea(AreaProcessing):
    """Represents an area which is plastered. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The closed contour of the area.
    apertures : :class:`Apertures`, optional
        The parts of the area which are not plastered.
    thickness : float, optional
        The thickness of the plaster.
    tool_id : int, optional
        The tool ID for the processing.

    """

    PROCESSING_NAME = "PlasterArea"  # type: ignore
    ATTRIBUTE_MAP = dict(AreaProcessing.ATTRIBUTE_MAP, Thickness=AttributeSpec("thickness", float, limits=(0.0, 1000.0), scales=True))


class InsulationArea(AreaProcessing):
    """Represents an area which is filled with insulation. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The closed contour of the area.
    part_ref_guid : str
        The GUID of the referenced insulation part, in curly braces.
    apertures : :class:`Apertures`, optional
        The parts of the area which are not insulated.

    """

    PROCESSING_NAME = "InsulationArea"  # type: ignore
    ATTRIBUTE_MAP = dict(AreaProcessing.ATTRIBUTE_MAP, PartRefGUID=AttributeSpec("part_ref_guid", str))

    @property
    def part_ref_guid(self):
        return self._part_ref_guid

    @part_ref_guid.setter
    def part_ref_guid(self, value):
        if not value or not re.match(r"^\{[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\}$", value):
            raise ValueError("part_ref_guid must be a GUID in curly braces. Got: {}".format(value))
        self._part_ref_guid = value


class LockoutArea(AreaProcessing):
    """Represents an area which the processings of the given kinds must keep out of. It leaves the geometry of the element as it is.

    Parameters
    ----------
    contour : :class:`SimpleContour`
        The closed contour of the area.
    for_marking, for_milling, for_sawing, for_nailing, for_gluing, for_planing, for_plastering, for_insulation, for_free_contour : bool, optional
        True if the area is locked for this kind of processing. Default is True.

    """

    PROCESSING_NAME = "LockoutArea"  # type: ignore
    ATTRIBUTE_MAP = {
        "Contour": AttributeSpec("contour", SimpleContour),
        "ForMarking": AttributeSpec("for_marking", bool, True),
        "ForMilling": AttributeSpec("for_milling", bool, True),
        "ForSawing": AttributeSpec("for_sawing", bool, True),
        "ForNailing": AttributeSpec("for_nailing", bool, True),
        "ForGluing": AttributeSpec("for_gluing", bool, True),
        "ForPlaning": AttributeSpec("for_planing", bool, True),
        "ForPlastering": AttributeSpec("for_plastering", bool, True),
        "ForInsulation": AttributeSpec("for_insulation", bool, True),
        "ForFreeContour": AttributeSpec("for_free_contour", bool, True),
    }
