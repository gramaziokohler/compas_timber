__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska", "Chen Kasirer", "Gonzalo Casas"]
__license__ = "MIT"
__version__ = "20.09.2022"

from compas_timber.utils.workflow import CollectionDef
import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error


def same_beams(beams1, beams2):
    return set(beams1) == set(beams2)
joints = []

#clean all Nones
joint_defaults = [_ for _ in Defaults if _]
joint_overrides = [_ for _ in Overrides if _]


if not joint_defaults and not joint_overrides:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameters Defaults and Overrides both failed to collect data")

elif joint_defaults and not joint_overrides:
    joints = joint_defaults

elif not joint_defaults and joint_overrides: 
    joints = joint_overrides

elif joint_defaults and joint_overrides:

    jd_jo = {k:[] for k in joint_defaults}
    jo_jd = {k:[] for k in joint_overrides}

    for jd in joint_defaults:
        for jo in joint_overrides:
            if same_beams(jd.beams, jo.beams):
                jd_jo[jd].append(jo)
                jo_jd[jo].append(jd)

    #filter defaults and overrides: if not override found, add default, otherwise add first override in the list (it's your problem if there are multiple)
    for k,v in jd_jo.items():
        if v: joints.append(v[0])
        else: joints.append(k)
    
    #add extras (joints in overrides for beam pairs not present in defaults)
    for k,v in jo_jd.items():
        if not v: joints.append(k)



JointsCollection = CollectionDef(joints)
