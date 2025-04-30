# r: compas_timber>=0.15.3
# flake8: noqa
from compas_timber.ghpython.ghcomponent_helpers import item_input_valid_cpython
from compas_timber.design.workflow import Attribute

n = item_input_valid_cpython(ghenv, Name, "Name")
v = item_input_valid_cpython(ghenv, Value, "Value")

if n and v:
    Attribute = Attribute(Name, Value)
