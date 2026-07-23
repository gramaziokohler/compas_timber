import re
from typing import Optional

from compas.geometry import Frame
from compas.geometry import Line

from .fastener import Fastener
from .fastener import FastenerPart


class Screw(FastenerPart):
    """
    Describe a screw that can be used as part of a fastener.

    Parameters
    ----------
    diameter : float
        The diameter of the screw in mm.
    length : float
        The length of the screw in mm.
    """

    def __init__(self, diameter: float, length: float, placement_frame: Optional[Frame] = None, **kwargs):
        super().__init__(frame=placement_frame, **kwargs)
        self.diameter = float(diameter)
        self.length = float(length)

    @property
    def __data__(self):
        # We store diameter and length. COMPAS automatically handles serializing 'name'
        return {
            "diameter": self.diameter,
            "length": self.length,
        }

    @property
    def designation(self) -> str:
        """Returns the standard engineering designation (e.g., 'Ø8x120')."""
        # Formats to 1 decimal place if it's a fractional size (like 5.5), otherwise integer
        d = f"{self.diameter:.1f}".rstrip("0").rstrip(".")
        l = f"{self.length:.1f}".rstrip("0").rstrip(".")
        return f"Ø{d}x{l}"

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

    def __repr__(self):
        return f"Screw({self.designation}, name='{self.name}')"


class FastenerScrew(Fastener):
    """
    A fastener that consists of one or more screws.

    Parameters
    ----------
    screws : list of Screw
        The screws that make up this fastener.
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

    def __repr__(self):
        return f"FastenerScrew(screws={len(self.screws)}, name='{self.name}')"
