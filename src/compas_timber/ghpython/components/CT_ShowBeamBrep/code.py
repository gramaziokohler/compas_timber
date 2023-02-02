# flake8: noqa
from compas_rhino.conversions import box_to_rhino

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid

if list_input_valid(ghenv, Beam, "Beam"):
    Brep = [box_to_rhino(b.shape).ToBrep() for b in Beam]
