from compas.scene import SceneObject
from compas_rhino.scene import RhinoSceneObject


class FeatureErrorObject(RhinoSceneObject):
    """

    Parameters
    ----------
    error_instance : :class:`~compas_timber.consumers.FeatureApplicationError`
        The error instance to visualize.

    """
    def __init__(self, error_instance, layer=None, **kwargs):
        super(FeatureErrorObject, self).__init__(layer=layer, item=error_instance, name="FeatureErrorObject")
        self.name = "FeatureErrorObject"
        self.error_instance = error_instance

    def draw(self):
        feature = self.error_instance.feature_geometry
        beam = self.error_instance.beam_geometry
        guids = [o.draw() for o in [self.add(feature), self.add(beam)]]
        return guids

