# flake8: noqa
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid
from compas_timber.ghpython.workflow import Attribute

n = item_input_valid(ghenv, Name, "Name")
v = item_input_valid(ghenv, Value, "Value")

if n and v:
    Attribute = Attribute(Name, Value)
