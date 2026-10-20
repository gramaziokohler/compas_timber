from __future__ import annotations

from typing import Optional

from compas.geometry import Frame

from .fastener import FastenerPart


# TODO: This perhaps is solvable directly with Element (because it takes arbitrary geometry)
# TODO: however, there's a more complex issue with set-geometry fasteners: they're visualizable only and do not provide any parameterization for the fabrication. to rethink.
class GeometryPart(FastenerPart):
    """
    Describes a fastener part defined by an explicit geometry. Can be used to add a custom fastener or a fastener coming
    from a library of fasteners.

    The geometry is defined in the part's local coordinate system; its placement in the model is expressed by the
    element ``transformation``.

    Parameters
    ----------
    geometry : Geometry
        The geometry of the part, in the part's local coordinate system.
    frame : Frame, optional
        The placement frame of the part. Defaults to the world XY frame.

    Attributes
    ----------
    geometry : Geometry
        The geometry of the part in model coordinates.
    """

    @property
    def __data__(self):
        return {"geometry": self._raw_geometry, "frame": self.placement_frame}

    def __init__(self, geometry, frame: Optional[Frame] = None, **kwargs):
        super().__init__(frame=frame, **kwargs)
        self._raw_geometry = geometry

    def compute_elementgeometry(self, include_features: bool = False):
        return self._raw_geometry.copy()
