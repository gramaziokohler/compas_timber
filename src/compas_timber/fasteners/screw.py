from __future__ import annotations

import re
from typing import Optional

from compas.geometry import Cone
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Transformation
from compas_brep import Brep

from compas_timber.fabrication import Drilling

from .anchor import AnchorKind
from .fastener import Fastener
from .fastener import FastenerPart


class Screw(FastenerPart):
    """
    Describes a countersunk timber screw that can be used as part of a fastener.

    Parameters
    ----------
    diameter : float
        The diameter of the screw shank.
    length : float
        The length of the screw shank.
    placement_frame : :class:`~compas.geometry.Frame`, optional
        The placement frame of the screw relative to its parent. Defaults to the world XY frame.
    precise : bool, optional
        If ``True``, :attr:`geometry` includes the conical countersunk head, unioned with the shank into a single
        Brep. If ``False`` (default), the geometry is just the cylindrical shank, which is cheaper to compute.
    head_diameter : float, optional
        The diameter of the countersunk head, at the material surface. Only used when ``precise`` is ``True``.
        Defaults to twice the shank diameter.
    head_length : float, optional
        The height of the conical head, measured from the surface outwards. Only used when ``precise`` is ``True``.
        Defaults to the shank diameter.

    Attributes
    ----------
    diameter : float
        The diameter of the screw shank.
    length : float
        The length of the screw shank.
    precise : bool
        Whether :attr:`geometry` includes the conical head.
    head_diameter : float
        The diameter of the countersunk head, at the material surface.
    head_length : float
        The height of the conical head.
    designation : str
        The standard engineering designation of the screw (e.g. 'Ø8x120').
    centerline : :class:`~compas.geometry.Line`
        The centerline of the screw, in local coordinates.
    blank_geometry : :class:`~compas.geometry.Cylinder`
        The shank geometry of the screw, in local coordinates.
    head_geometry : :class:`~compas.geometry.Cone`
        The conical head geometry of the screw, in local coordinates.
    """

    @property
    def __data__(self):
        # We store diameter and length. COMPAS automatically handles serializing 'name'
        return {
            "diameter": self.diameter,
            "length": self.length,
            "precise": self.precise,
            "head_diameter": self.head_diameter,
            "head_length": self.head_length,
            "placement_frame": self.placement_frame,
            "element_guids": self.element_guids,
        }

    def __init__(
        self,
        diameter: float,
        length: float,
        placement_frame: Optional[Frame] = None,
        precise: bool = False,
        head_diameter: Optional[float] = None,
        head_length: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(frame=placement_frame, **kwargs)
        self.diameter = float(diameter)
        self.length = float(length)
        self.precise = precise
        self.head_diameter = float(head_diameter) if head_diameter is not None else self.diameter * 2.0
        self.head_length = float(head_length) if head_length is not None else self.diameter

    @property
    def designation(self) -> str:
        """Returns the standard engineering designation (e.g., 'Ø8x120')."""
        # Formats to 1 decimal place if it's a fractional size (like 5.5), otherwise integer
        diameter = f"{self.diameter:.1f}".rstrip("0").rstrip(".")
        length = f"{self.length:.1f}".rstrip("0").rstrip(".")
        return f"Ø{diameter}x{length}"

    @classmethod
    def from_name(cls, name: str, placement_frame: Optional[Frame] = None, **kwargs):
        """
        Create a Screw instance from a standard designation string.

        Supports formats like: "8x120", "Ø8x120", "8.0x120", "D8 x 120"

        Parameters
        ----------
        name : str
            The name string (e.g., "8x120").
        """
        # Parse the dimension string
        pattern = r"(?:[Ø\D]*)\s*(\d+(?:\.\d+)?)\s*[xX\*]\s*(\d+(?:\.\d+)?)"
        match = re.search(pattern, name)

        if not match:
            raise ValueError(f"Could not parse screw name '{name}'. Please use a format like '8x120' or 'Ø10x200'.")

        diameter = float(match.group(1))
        length = float(match.group(2))

        # We can still pass the clean parsed name as the COMPAS 'name' attribute
        # so it displays nicely in the CAD hierarchy.
        clean_name = f"Ø{match.group(1)}x{match.group(2)}"
        kwargs.setdefault("name", clean_name)

        return cls(diameter=diameter, length=length, placement_frame=placement_frame, **kwargs)

    @property
    def centerline(self) -> Line:
        sp = self._local_frame.point
        ep = self._local_frame.point + (-self._local_frame.zaxis * self.length)
        return Line(sp, ep)

    @property
    def _local_frame(self) -> Frame:
        return Frame.worldXY()

    @property
    def blank_geometry(self) -> Cylinder:
        cylinder_frame = Frame(self._local_frame.point, self._local_frame.xaxis, self._local_frame.yaxis)
        cylinder = Cylinder(self.diameter / 2, self.length, cylinder_frame)
        cylinder.frame.point += self._local_frame.zaxis * (-self.length / 2)
        return cylinder

    @property
    def head_geometry(self) -> Cone:
        # base circle (head_diameter) flush with the material surface (local origin), apex pointing inwards along -z;
        # unioned with the shank, this yields a frustum-shaped countersunk head that tapers down to the shank
        # diameter and blends into it (the part of the cone beyond that point ends up inside the shank solid)
        head_frame = Frame(self._local_frame.point, -self._local_frame.xaxis, self._local_frame.yaxis)
        return Cone(self.head_diameter / 2, self.head_length, head_frame)

    def compute_elementgeometry(self, include_features: bool = False) -> Brep:
        shank_brep = Brep.from_cylinder(self.blank_geometry)
        if not self.precise:
            return shank_brep
        head_brep = Brep.from_cone(self.head_geometry)
        return shank_brep + head_brep

    def apply_fastening_features(self) -> None:
        """Apply the fabrication features generated by this screw to :attr:`elements`.

        The screw is assumed to be a cylindrical hole in its elements. The hole is centered on the screw's placement
        frame and has the same diameter as the screw.
        """
        xform = self.modeltransformation
        for element in self.elements:
            drill_line = self.centerline
            drill_line.transform(xform)
            drilling = Drilling.from_line_and_element(drill_line, element, self.diameter)
            element.add_feature(drilling)

    def __repr__(self):
        return f"Screw({self.designation}, name='{self.name}')"


class ScrewFastener(Fastener):
    """
    A fastener that consists of one or more screws, placed at every anchor it is bound to.

    The screws describe a reusable pattern: each screw's own placement frame expresses its position relative to the
    anchor it will be bound to (e.g. an offset within a group of screws), defaulting to the anchor's frame itself.

    Parameters
    ----------
    screws : list of :class:`Screw`
        The screws that make up this fastener's pattern.

    Attributes
    ----------
    ACCEPTS : list of :class:`~compas_timber.fasteners.AnchorKind`
        The kinds of anchor this fastener binds to.
    """

    ACCEPTS = [AnchorKind.AXIS, AnchorKind.POINT]

    def __init__(self, screws: list[Screw], **kwargs):
        super().__init__(**kwargs)
        self.screws = screws

    @property
    def __data__(self):
        return {
            "screws": [screw.__data__ for screw in self.screws],
        }

    def bind(self, anchors: list) -> "ScrewFastener":
        """Bind the fastener to a set of anchors, staging a copy of every screw in the pattern at each.

        Parameters
        ----------
        anchors : list of :class:`~compas_timber.fasteners.FastenerAnchor`
            The anchors to place the screw pattern at. Every anchor must be of a kind this fastener accepts.

        Returns
        -------
        :class:`~compas_timber.fasteners.ScrewFastener`
            The fastener itself, for chaining.

        Raises
        ------
        ValueError
            If any of the anchors are not of a kind this fastener accepts.
        """
        anchors = list(anchors)
        wrong = [anchor for anchor in anchors if anchor.kind not in self.ACCEPTS]
        if wrong:
            raise ValueError("{} accepts {} anchors, got {}.".format(type(self).__name__, self.ACCEPTS, [anchor.kind for anchor in wrong]))

        for anchor in anchors:
            anchor_transformation = Transformation.from_frame(anchor.frame)
            for screw in self.screws:
                placed = Screw(
                    screw.diameter,
                    screw.length,
                    precise=screw.precise,
                    head_diameter=screw.head_diameter,
                    head_length=screw.head_length,
                    name=screw.name,
                )
                placed.transformation = anchor_transformation * (screw.transformation or Transformation())
                placed.elements = list(anchor.elements)
                self.add_part(placed)
        return self

    def __repr__(self):
        return f"FastenerScrew(screws={len(self.screws)}, name='{self.name}')"
