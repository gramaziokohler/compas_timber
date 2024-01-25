import compas_rhino
from compas.plugins import plugin
from compas.scene import register

from compas_timber.consumers import FeatureApplicationError

from .featureerrorobject import FeatureErrorObject


@plugin(category="drawing-utils", pluggable_name="clear", requires=["Rhino"])
def clear_rhino(guids=None):
    compas_rhino.clear(guids=guids)


@plugin(category="drawing-utils", pluggable_name="redraw", requires=["Rhino"])
def redraw_rhino():
    compas_rhino.redraw()


@plugin(category="drawing-utils", pluggable_name="clear", requires=["Grasshopper"])
def clear_GH(guids=None):
    pass


@plugin(category="drawing-utils", pluggable_name="redraw", requires=["Grasshopper"])
def redraw_GH():
    pass


@plugin(category="factories", requires=["Rhino"])
def register_scene_objects():
    register(FeatureApplicationError, FeatureErrorObject, "Grasshopper")
    print("COMPAS Timber Rhino SceneObjects registered.")


__all__ = [
    "FeatureErrorObject",
]
