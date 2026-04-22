from compas.geometry import Frame
from compas.geometry import Transformation

from .part import Part


class GeometryPart(Part):
    """
    Describes a fastener part defined by a geometry. Can be used to add a custom fastener or coming from a library of fasteners.


    Parameters
    ----------
    geometry : Geometry
        The geometry of the part.
    frame : Frame, optional
        The frame of the part, by default Frame.worldXY().

    Attributes
    ----------
    geometry : Geometry
        The geometry of the part, transformed to the part's frame.
    frame : Frame
        The frame of the part.

    """

    def __init__(self, geometry, frame=None):
        super().__init__()
        self.frame = frame or Frame.worldXY()
        self._geometry = geometry

    @property
    def __data__(self):
        data = super().__data__
        data["type"] = "GeometryPart"
        data["geometry"] = self._geometry
        data["frame"] = self.frame.__data__
        return data

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

    @classmethod
    def from_data(cls, data):
        geometry = data["geometry"]
        frame_data = data["frame"]
        frame = Frame(frame_data["point"], frame_data["xaxis"], frame_data["yaxis"])
        part = cls(geometry, frame)
        guid = data["guid"]
        part.guid = guid
        return part

    def copy(self):
        return GeometryPart(self._geometry.copy(), self.frame.copy())

    def apply_features(self, elements):
        pass
