import Rhino.Geometry as rg

from compas_rhino.conversions import point_to_rhino, vector_to_rhino, frame_to_rhino 
from compas_rhino.conversions import box_to_rhino

from compas_timber.assembly import TimberAssembly
from compas_timber.connections import TButtJoint 
from compas_timber.connections import LMiterJoint
from compas_timber.connections import LButtJoint

from copy import deepcopy

import Grasshopper.Kernel as ghk

warning = ghk.GH_RuntimeMessageLevel.Warning
error = ghk.GH_RuntimeMessageLevel.Error
remark = ghk.GH_RuntimeMessageLevel.Remark

if not BeamsCollection:
    ghenv.Component.AddRuntimeMessage(warning, "Input parameter BeamsCollection failed to collect data")

#clean up Nones and other stuff=================================================
if BeamsCollection:
    beams = BeamsCollection.objs
else: 
    beams=[]

if JointsCollection:
    joints = JointsCollection.objs
else:
    joints = []

if FeaturesCollection:
    features = FeaturesCollection.objs
else:
    features = []

if BeamsCollection and not beams:
    ghenv.Component.AddRuntimeMessage(warning, "There are no Beams in the BeamsCollection")
else:

    #create assembly================================================================
    assembly = TimberAssembly()

    #add beams======================================================================
    for i,beam in enumerate(beams): 
        beam.attributes['id']=i
        assembly.add_beam(beam, key=i)

    #change beam refs to keys=======================================================
    joints_list = [(j.joint_type, [b.key for b in j.beams]) for j in joints ]
    features_list = [(f.feature_type, f.feature_shape, f.beam.key) for f in features]

    assembly = deepcopy(assembly)

    #add joints=====================================================================

    for joint_type, beams in joints_list:
        beamA = assembly.find_by_key(beams[0])
        beamB = assembly.find_by_key(beams[1])
        if joint_type == 'T-Butt':
            TButtJoint(assembly, beamA, beamB)
        elif joint_type == 'L-Miter':
            LMiterJoint(assembly, beamA, beamB)
        elif joint_type == 'L-Butt':
            LButtJoint(assembly, beamA, beamB)

    print "Created following joints:"
    for j in assembly.joints: print "    ",j

    #add features===================================================================
    L_joints = [j for j in assembly.joints if j.joint_type[0]=="L"]
    other_joints = [j for j in assembly.joints if j.joint_type[0]!="L"]

    for j in L_joints:
        j.add_features()
    for j in other_joints:
        j.add_features()

    for feature_type, shape, beam in features_list:
            beam = assembly.find_by_key(beam)
            beam.add_feature(shape,feature_type)

    #apply features=================================================================
    if not apply:
        brep_model = [box_to_rhino(beam.shape).ToBrep() for beam in assembly.beams]
    else:
        brep_model = []
        for beam in assembly.beams:
            print "-----------------\n beam %s --> %s feature(s)"%( beam.key, len(beam.features))
            for f in beam.features: print "    ", f
            #consolidate and apply extend features first
            extend_features = [f for f in beam.features if f[1] == "extend"] #f: [ds,de],'extend'
            if extend_features:
                ext_start = min([f[0][0] for f in extend_features])
                ext_end   = max([f[0][1] for f in extend_features])
                beam.extend_ends(ext_start, ext_end)
            
            boxbrep = box_to_rhino(beam.shape).ToBrep()
            
            def trim_brep(brep,plns):
                bi = brep
                for pi in plns:
                    pi.Flip()
                    bx = rg.Brep.Trim(bi,pi,1e-6)
                    if len(bx)==0:
                        print("trim failed - nothing trimmed?")
                    elif len(bx)==1:
                        bi=bx[0].CapPlanarHoles(1e-6)
                    else:
                        print("%s parts after trimming - adding none"%len(bx))
                return bi

            trim_features = [f for f in beam.features if f[1] == "trim"]
            plns = [frame_to_rhino(f[0]) for f in trim_features]
            brep_trimmed = trim_brep(boxbrep,plns)

            beam.brep = brep_trimmed
            brep_model.append(brep_trimmed)

    Breps = brep_model
    Assembly = assembly

