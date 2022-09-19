__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.utils.ghpython import list_input_valid


o = list_input_valid(ghenv,refObj, "refObj")
a = list_input_valid(ghenv,Attribute, "Attribute")

if update and o and a:
    for attr in Attribute:
        if attr:
            for guid in refObj:
                if guid:
                    update_rhobj_attributes_name(guid, attr.name, attr.value)