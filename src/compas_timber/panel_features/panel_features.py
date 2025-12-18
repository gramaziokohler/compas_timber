from abc import ABC

from compas.geometry import Frame
from compas.geometry import Geometry
from compas.geometry import Transformation
from compas_model.elements import Element


class PanelFeatureType:
    CONNECTION_INTERFACE = "CONNECTION_INTERFACE"
    RECESS = "RECESS"
    OPENING = "OPENING"
    LINEAR = "LINEAR"
    VOLUMETRIC = "VOLUMETRIC"
    NONE = "NONE"


class PanelFeature(Element, ABC):
    def __init__(self, frame: Frame, panel_feature_type: PanelFeatureType | str = PanelFeatureType.NONE, name: str | None = None, **kwargs) -> None:
        super(PanelFeature, self).__init__(transformation=Transformation.from_frame(frame), **kwargs)
        self.panel_feature_type = panel_feature_type
        self.name = name

    @property
    def __data__(self) -> dict:
        data = super(PanelFeature, self).__data__
        data["frame"] = Frame.from_transformation(data.pop("transformation"))
        return data

    @property
    def geometry(self) -> Geometry:
        """The geometry of the element in the model's global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_modelgeometry()
        return self._geometry

    def compute_modeltransformation(self) -> Transformation:
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()

    def compute_modelgeometry(self) -> Geometry:
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)
        return super().compute_modelgeometry()
