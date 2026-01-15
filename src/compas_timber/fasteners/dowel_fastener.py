from __future__ import annotations

from compas.geometry import Frame
from compas.tolerance import Tolerance

from compas_timber.fasteners.fastener import Fastener

TOL = Tolerance()


class Dowel(Fastener):
    """Class description"""

    def __init__(self, frame: Frame, height: float, radius: float):
        super().__init__(frame=frame)
        self.height = height
        self.radius = radius
        self.interfaces = []
        self._shape = None
