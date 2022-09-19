__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas_timber.utils.ghpython import list_input_valid
from compas_rhino.conversions import box_to_rhino

if list_input_valid(ghenv, Beam, "Beam"):
    Brep = [box_to_rhino(b.shape).ToBrep() for b in Beam]