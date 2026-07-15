from __future__ import annotations

from typing import Optional

from compas.data import Data
from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import angle_vectors
from compas_brep import Brep

from compas_timber.fabrication import Drilling
from compas_timber.fabrication import Pocket

from .anchor import AnchorKind
from .fastener import Fastener
from .fastener import FastenerPart


def beam_ref_side_incidence_vector(beam, vector, ignore_ends=True):
    if ignore_ends:
        ref_sides = beam.ref_sides[:4]
    else:
        ref_sides = beam.ref_sides

    ref_side_angles = {}
    for ref_side_index, ref_side in enumerate(ref_sides):
        ref_side_angles[ref_side_index] = angle_vectors(ref_side.normal, vector)

    return ref_side_angles


def beam_ref_side_index(beam, vector):
    ref_side_dict = beam_ref_side_incidence_vector(beam, vector)
    ref_side_index = min(ref_side_dict, key=lambda k: ref_side_dict[k])
    return ref_side_index


class RectangularPlate(FastenerPart):
    """
    Describes a rectangular plate that can be used as part of a fastener.

    It has a width, height, thickness, and can have holes. The plate can create a recess (Pocket feature) in the beam.

    The plate geometry is defined in the part's local coordinate system (centered on the world XY frame); its placement
    in the model is expressed by the element ``transformation`` (see :class:`~compas_timber.elements.FastenerPart`).

    Parameters
    ----------
    width : float
        The width of the plate (xaxis of the local frame).
    height : float
        The height of the plate (yaxis of the local frame).
    thickness : float
        The thickness of the plate (zaxis of the local frame).
    frame : Frame, optional
        The placement frame of the plate. Defaults to the world XY frame.
    recess : float, optional
        The depth of the recess to be milled in the beam, by default 0 (no recess).
    recess_offset : float, optional
        The offset of the recess from the plate dimensions, by default 0 (recess has the same dimensions as the plate).
    holes : list[PlateHole], optional
        The holes of the plate, expressed in the plate's local coordinate system.

    Attributes
    ----------
    width : float
        The width of the plate.
    height : float
        The height of the plate.
    thickness : float
        The thickness of the plate.
    holes : list[PlateHole]
        The holes in the plate.
    recess : float
        The depth of the recess to be milled in the beam.
    recess_offset : float
        The offset of the recess from the plate dimensions.
    geometry : Brep
        The geometry of the plate with holes as a Brep, in model coordinates.
    blank_geometry : Polyhedron
        The geometry of the plate without holes as a Polyhedron, in local coordinates.

    """

    @property
    def __data__(self):
        return {
            "width": self.width,
            "height": self.height,
            "thickness": self.thickness,
            "frame": self.placement_frame,
            "recess": self.recess,
            "recess_offset": self.recess_offset,
            "holes": self.holes,
        }

    def __init__(
        self,
        width: float,
        height: float,
        thickness: float,
        frame: Optional[Frame] = None,
        recess: float = 0,
        recess_offset: float = 0,
        holes: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(frame=frame, **kwargs)
        self.width = width
        self.height = height
        self.thickness = thickness
        self.recess = recess
        self.recess_offset = recess_offset
        self.holes = list(holes) if holes else []

    @property
    def _local_frame(self) -> Frame:
        # the plate geometry and holes are defined relative to this frame
        return Frame.worldXY()

    @property
    def blank_geometry(self):
        box = Box(self.width, self.height, self.thickness, frame=self._local_frame)
        box.frame.point += self._local_frame.zaxis * self.thickness / 2
        box = box.to_polyhedron()
        return box

    def compute_elementgeometry(self, include_features: bool = False) -> Brep:
        box = self.blank_geometry
        box_brep = Brep.from_mesh(box.to_mesh())
        for hole in self.holes:
            box_brep -= hole.geometry
        if self.recess > 0:
            box_brep.translate(self._local_frame.zaxis * -self.recess)
        return box_brep

    def add_hole_point_diameter(self, point: Point, diameter: float, apply_drilling=True, drilling_depth=5, drilling_diameter=2) -> PlateHole:
        """
        Add a hole by specifying the point and the diameter of the hole.

        Parameters
        ----------
        point : Point
            The point where the hole should be added, relative to the plate's local frame.
        diameter : float
            The diameter of the hole.
        apply_drilling : bool, optional
            Whether to apply drilling for this hole, by default True.
        drilling_depth : float, optional
            The depth of the drilling, by default 5.
        drilling_diameter : float, optional
            The diameter of the drilling, by default 2.

        Returns
        -------
        PlateHole
            The created PlateHole object.

        """
        local = self._local_frame
        hole_frame = local.copy()
        hole_frame.point = local.point + local.xaxis * point.x + local.yaxis * point.y + local.zaxis * point.z
        hole = PlateHole(hole_frame, diameter, self.thickness, apply_drilling=apply_drilling, drilling_depth=drilling_depth, drilling_diameter=drilling_diameter)
        self.add_hole(hole)
        return hole

    def add_hole(self, hole: PlateHole):
        """
        Add a hole to the plate.

        Parameters
        ----------
        hole : PlateHole
            The hole to be added to the plate, expressed in the plate's local coordinate system.
        """
        self.holes.append(hole)

    def add_holes_grid(self, nx: int, ny: int, border_padding: float, diameter: float, apply_drilling=True, drilling_depth=None, drilling_diameter=None) -> list:
        """
        Add a grid of holes to the plate.

        Parameters
        ----------
        nx : int
            The number of holes in the x direction.
        ny : int
            The number of holes in the y direction.
        border_padding : float
            The padding from the border of the plate to the first and last holes.
        diameter : float
            The diameter of the holes.

        Returns
        -------
        list[PlateHole]
            The created PlateHole objects.
        """
        holes = []
        for ix in range(nx):
            for iy in range(ny):
                x = self._local_frame.point.x + border_padding + ix * (self.width - 2 * border_padding) / (nx - 1)
                x -= self.width / 2

                y = self._local_frame.point.y + border_padding + iy * (self.height - 2 * border_padding) / (ny - 1)
                y -= self.height / 2

                if not drilling_depth:
                    apply_drilling = False

                if not drilling_diameter:
                    drilling_diameter = diameter

                hole = self.add_hole_point_diameter(Point(x, y, 0), diameter, apply_drilling, drilling_depth, drilling_diameter)
                holes.append(hole)
        return holes

    def apply_fastening_features(self, elements):
        """
        Apply the features of the plate to the given elements.
        This includes creating pockets for the recess and drillings for the holes.

        Parameters
        ----------
        elements : list[Element]
            The elements to which the features of the plate should be applied.
        """
        frame = self.frame  # placement frame in model coordinates
        xform = self.modeltransformation
        for element in elements:
            ref_side_index = beam_ref_side_index(element, frame.zaxis)

            # recess Pocket
            geo = self._compute_recess_milling_volume(frame)
            if geo:
                pocket = Pocket.from_volume_and_element(geo, element, ref_side_index=ref_side_index)
                element.add_feature(pocket)

            # Drillings
            for hole in self.holes:
                if not hole.apply_drilling:
                    continue
                hole_frame = hole.frame.transformed(xform)  # to model coordinates
                start = hole_frame.point + frame.zaxis * self.thickness
                end = hole_frame.point + frame.zaxis * -(self.thickness + self.recess)
                drill_line = Line(start, end)
                try:
                    drilling = Drilling.from_line_and_element(drill_line, element, hole.drilling_diameter)
                    element.add_feature(drilling)
                except Exception:
                    pass

    def _compute_recess_milling_volume(self, frame):
        if self.recess <= 0:
            return None
        recess_box = Box(xsize=(self.width + self.recess_offset * 2), ysize=(self.height + self.recess_offset * 2), zsize=self.recess, frame=frame)
        recess_box.frame.point.translate(-frame.zaxis * (self.recess / 2))
        return recess_box.to_polyhedron()


# TODO: shouldn't this be a FastenerPart?
class PlateHole(Data):
    """
    Describes a hole in a fastener plate.
    It has a diameter, a height, and a frame that describes its position and orientation relative to the plate's local
    coordinate system.
    It can apply a `Drilling` fabrication process to the beam, in which case it has a drilling depth and diameter.


    Parameters
    ----------
    frame : Frame
        The frame of the hole, describing its position and orientation relative to the plate's local coordinate system.
    diameter : float
        The diameter of the hole.
    height : float
        The height of the hole, i.e. the thickness of the plate.
    apply_drilling : bool, optional
        Whether to apply a drilling process to the beam, by default True.
    drilling_depth : float, optional
        The depth of the drilling process to be applied to the beam, by default 5.
    drilling_diameter : float, optional
        The diameter of the drilling process to be applied to the beam, by default is the same as the diameter.

    """

    @property
    def __data__(self):
        return {
            "frame": self.frame,
            "diameter": self.diameter,
            "height": self.height,
            "apply_drilling": self.apply_drilling,
            "drilling_depth": self.drilling_depth,
            "drilling_diameter": self.drilling_diameter,
        }

    def __init__(
        self, frame: Frame, diameter: float, height: float, apply_drilling: bool = True, drilling_depth: Optional[float] = None, drilling_diameter: Optional[float] = None
    ):
        super().__init__()
        self.frame = frame
        self.diameter = diameter
        self.height = height
        self.apply_drilling = apply_drilling
        self.drilling_depth = drilling_depth if drilling_depth is not None else 5
        self.drilling_diameter = drilling_diameter if drilling_diameter is not None else diameter

    def copy(self):
        return PlateHole(self.frame.copy(), self.diameter, self.height, self.apply_drilling, self.drilling_depth, self.drilling_diameter)

    @property
    def geometry(self):
        cylinder = Cylinder(radius=self.diameter / 2, height=self.height, frame=self.frame)
        cylinder.frame.point += cylinder.frame.zaxis * self.height / 2
        cylinder_brep = cylinder.to_brep()
        return cylinder_brep

    @property
    def drilling_line(self) -> Line:
        start = self.frame.point
        end = self.frame.point.translated(self.frame.zaxis * -self.drilling_depth)
        line = Line(start, end)
        return line


class PlateFastener(Fastener):
    """A fastener consisting of one rectangular plate per anchor, placed on the faces a joint exposes.

    This is the "what" half of the anchor-based fastener system: it is joint-agnostic. It declares the kind of anchor it
    consumes (``FACE``) and, when bound to a set of anchors, stages one plate part at each of them (repeat-per-anchor
    cardinality). The plate parts become children of the fastener once it is added to a model.

    Parameters
    ----------
    width : float
        The width of the plate (along the anchor x-axis).
    height : float
        The height of the plate (along the anchor y-axis).
    thickness : float
        The thickness of the plate.
    recess : float, optional
        The depth of the recess milled into the hosting element. Default is 0.0 (no recess).
    recess_offset : float, optional
        The offset of the recess relative to the plate dimensions. Default is 0.0.

    Attributes
    ----------
    ACCEPTS : :class:`~compas_timber.fasteners.AnchorKind`
        The kind of anchor this fastener binds to.
    """

    ACCEPTS = AnchorKind.FACE

    @property
    def __data__(self):
        data = super().__data__
        data["width"] = self.width
        data["height"] = self.height
        data["thickness"] = self.thickness
        data["recess"] = self.recess
        data["recess_offset"] = self.recess_offset
        return data

    def __init__(self, width: float, height: float, thickness: float, recess: float = 0.0, recess_offset: float = 0.0, **kwargs):
        super(PlateFastener, self).__init__(**kwargs)
        self.width = width
        self.height = height
        self.thickness = thickness
        self.recess = recess
        self.recess_offset = recess_offset

    def bind(self, anchors: list) -> "PlateFastener":
        """Bind the fastener to a set of anchors, staging one plate part at each.

        Parameters
        ----------
        anchors : list of :class:`~compas_timber.fasteners.FastenerAnchor`
            The anchors to place the plate at. Every anchor must be of the kind this fastener accepts.

        Returns
        -------
        :class:`~compas_timber.fasteners.PlateFastener`
            The fastener itself, for chaining.

        Raises
        ------
        ValueError
            If any anchor is not of the accepted kind.
        """
        anchors = list(anchors)
        wrong = [anchor for anchor in anchors if anchor.kind is not self.ACCEPTS]
        if wrong:
            raise ValueError("{} accepts {} anchors, got {}.".format(type(self).__name__, self.ACCEPTS, [anchor.kind for anchor in wrong]))

        # one plate part is staged per anchor (repetition, not spanning)
        for anchor in anchors:
            plate = RectangularPlate(width=self.width, height=self.height, thickness=self.thickness, recess=self.recess, recess_offset=self.recess_offset)
            plate.transformation = Transformation.from_frame(anchor.frame)
            self.add_part(plate)
        return self
