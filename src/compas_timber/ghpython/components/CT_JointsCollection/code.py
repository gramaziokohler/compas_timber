
from compas_timber.utils.workflow import CollectionDef

def same_beams(beams1, beams2):
    return set(beams1) == set(beams2)
joints = []

joint_defaults = Defaults
joint_overrides = Overrides

if joint_defaults and not joint_overrides:
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
