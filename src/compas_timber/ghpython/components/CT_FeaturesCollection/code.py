# flake8: noqa
from compas_timber.utils.ghpython import list_input_valid
from compas_timber.utils.workflow import CollectionDef

if list_input_valid(ghenv, Features, "Features"):
    FeaturesCollection = CollectionDef(Features)
