from compas_timber.utils.workflow import guess_joint_topology_2beams
from compas_timber.utils.workflow import JointDefinition

import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error

if not BeamsCollection:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter BeamsCollection failed to ceollect data")
if not JointRules:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter JointRules failed to ceollect data")


tol = 1e-3

# find what kind of joint topology it looks like based on centerlines===========

connectivity = {'L':[],
                'T':[],
                'X':[]}

if BeamsCollection and JointRules:
    
    beams = BeamsCollection.objs
    groups = set([beam.attributes['group'] for beam in beams])
    
    
    n = len(beams)
    for gr in groups:
        for i in range(n-1):
            if beams[i].attributes['group']!=gr: continue
            
            for j in range(i+1,n):
                if beams[j].attributes['group']!=gr: continue
                jointtype, beams_pair = guess_joint_topology_2beams(beams[i], beams[j], tol=tol, max_distance = Dmax)
                if jointtype:
                    connectivity[jointtype].append(beams_pair)
    
    
    #Rephrase joint rules into a dict of {'cat+cat':type,}==========================
    joint_rules_dict = {}
    for jr in JointRules: 
        key = "%s+%s"%(jr[0],jr[1])
        if key in joint_rules_dict.keys():
            raise UserWarning("Conflicting rules detected for %s"%key)
        joint_rules_dict[key]=jr[2]
        
    joint_rules_dict = (joint_rules_dict )
    
    
    #Assign joint types depending on the auto-found connectivity type:
    log_no_def = []
    log_topo_mismatch = []
    
    joints_def =  []
    
    
    for beamA,beamB in connectivity['T']:
        catA, catB = (beamA.attributes['category'],beamB.attributes['category'])
        key = "%s+%s"%(catA,catB)
        try: joint_type = joint_rules_dict[key]
        except: log_no_def.append(('T', catA, catB))
        else:
            if joint_type[0]!='T': 
                log_topo_mismatch.append(('T', catA, catB, beams.index(beamA), beams.index(beamB), joint_rules_dict[key]))
            else:
                joints_def.append(JointDefinition(joint_type, (beamA,beamB)) ) 
    
    
    for beamA,beamB in connectivity['L']:
        catA, catB = (beamA.attributes['category'],beamB.attributes['category'])
        key = "%s+%s"%(catA,catB)
        try: joint_type = joint_rules_dict[key]
        except: log_no_def.append(('L', catA, catB))
        else:
            if joint_type[0]!='L': 
                log_topo_mismatch.append(('L', catA, catB, beams.index(beamA),beams.index(beamB), joint_rules_dict[key]))
            else:
                joints_def.append(JointDefinition(joint_type, (beamA,beamB)) ) #L-Miter, L-Butt
    
    
    for beamA,beamB in connectivity['X']:
        catA, catB = (beamA.attributes['category'],beamB.attributes['category'])
        key = "%s+%s"%(catA,catB)
        try: joint_type = joint_rules_dict[key]
        except: log_no_def.append(('X', catA, catB))
        else:
            if joint_type[0]!='X': 
                log_topo_mismatch.append(('X', catA, catB, beams.index(beamA),beams.index(beamB), joint_rules_dict[key]))
            else:
                pass #NOT IMPLEMENTED 
    
    
    #output
    Joints = joints_def
    
    #print logs
    log_no_def = set(log_no_def)
    log_topo_mismatch = set(log_topo_mismatch)
    
    topo_txt="Pairs of beams found for T,X,L topologies based on centerlines:\n"
    for key in connectivity.keys():
        topo_txt+="%s: %s\n"%(key,[(beams.index(beamA),beams.index(beamB)) for beamA,beamB in connectivity[key]])
    
    
    txt=""
    if log_no_def:
        txt += "Connections found for which no matching rules were found:\n"
        for t,b1,b2 in log_no_def:
            txt+="%s+%s with topology %s\n"%(b1,b2,t)
    
    if log_topo_mismatch:
        txt+="\nConnections found with a mismatch between rules and the actual topology:\n"
        for t,c1,c2,b1,b2,d in log_topo_mismatch:
            txt+="%s+%s (%s+%s) is %s --> cannot apply %s\n"%(c1,c2,b1,b2,t,d)
    
    Info = topo_txt+txt