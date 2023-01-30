# flake8: noqa
from compas_timber.utils.workflow import Attribute
from compas_timber.utils.ghpython import item_input_valid

n = item_input_valid(ghenv, Name, "Name")
v = item_input_valid(ghenv, Value, "Value")

if n and v:
    Attribute = Attribute(Name, Value)
