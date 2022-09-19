__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas_timber.utils.workflow import Attribute
from compas_timber.utils.ghpython import item_input_valid

n = item_input_valid(ghenv,Name,"Name")
v = item_input_valid(ghenv,Value,"Value")

if n and v:
    Attribute = Attribute(Name,Value)