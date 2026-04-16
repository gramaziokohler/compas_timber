from compas.geometry import Frame
from compas.geometry import Transformation


class GeometryPart:
    """
    This fasteners part contains only the geometry, of the fastener.
    """

    def __init__(self, geometry, frame=None):
        self.frame = frame or Frame.worldXY()
        self._geometry = geometry

    @property
    def frame(self) -> Frame:
        return self._frame

    @frame.setter
    def frame(self, value: Frame):
        if not isinstance(value, Frame):
            raise ValueError("Frame should be a Frame.")
        self._frame = value

    @property
    def geometry(self):
        geometry = self._geometry.copy()
        transformation = Transformation.from_frame_to_frame(Frame.worldXY(), self.frame)
        geometry.transform(transformation)
        return geometry

    def copy(self):
        return GeometryPart(self._geometry.copy(), self.frame.copy())

    def apply_features(self, elements):
        pass
