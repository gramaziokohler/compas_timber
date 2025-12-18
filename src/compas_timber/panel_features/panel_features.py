from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Transformation


class PanelFeatureType:
    CONNECTION_INTERFACE = "CONNECTION_INTERFACE"
    RECESS = "RECESS"
    OPENING = "OPENING"
    LINEAR = "LINEAR"
    VOLUMETRIC = "VOLUMETRIC"
    NONE = "NONE"


class PanelFeature(Data):
    # TODO: should this inherit from Element?
    def __init__(self, frame, panel_feature_type=PanelFeatureType.NONE, name=None):
        super(PanelFeature, self).__init__()
        self.panel_feature_type = panel_feature_type
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
