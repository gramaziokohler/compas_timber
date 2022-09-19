__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas_timber.utils.workflow import CollectionDef
from compas_timber.utils.ghpython import list_input_valid


if list_input_valid(ghenv, Features, "Features"):
    FeaturesCollection = CollectionDef(Features)