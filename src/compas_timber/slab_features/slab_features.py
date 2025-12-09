from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Transformation


class SlabFeatureType:
    CONNECTION_INTERFACE = "CONNECTION_INTERFACE"
    RECESS = "RECESS"
    OPENING = "OPENING"
    LINEAR = "LINEAR"
    VOLUMETRIC = "VOLUMETRIC"
    NONE = "NONE"


class SlabFeature(Data):
    # TODO: should this inherit from Element?
    def __init__(self, frame, slab_feature_type=SlabFeatureType.NONE, name=None):
        super(SlabFeature, self).__init__()
        self.slab_feature_type = slab_feature_type
        self.transformation = Transformation.from_frame(frame)
        self.name = name

    @property
    def __data__(self):
        data = {"frame": self.frame}
        return data

    @property
    def frame(self):
        return Frame.from_transformation(self.transformation)

    def transform(self, transformation):
        self.transformation = transformation * self.transformation

    def transformed(self, transformation):
        new = self.copy()
        new.transform(transformation)
        return new
