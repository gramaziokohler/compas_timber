from compas_timber.utils.workflow import CollectionDef
from compas_timber.utils.ghpython import list_input_valid


if list_input_valid(ghenv, Features, "Features"):
    FeaturesCollection = CollectionDef(Features)