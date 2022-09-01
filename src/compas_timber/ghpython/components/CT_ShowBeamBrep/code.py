from compas_timber.utils.ghpython import list_input_valid
from compas_rhino.conversions import box_to_rhino

if list_input_valid(ghenv, Beam, "Beam"):
    Brep = [box_to_rhino(b.shape).ToBrep() for b in Beam]