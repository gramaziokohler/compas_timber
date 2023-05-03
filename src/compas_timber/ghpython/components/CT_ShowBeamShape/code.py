# flake8: noqa
from compas_rhino.conversions import box_to_rhino

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid

if list_input_valid(ghenv.Component, Beam, "Beam"):
    Box = [box_to_rhino(b.shape) for b in Beam]
