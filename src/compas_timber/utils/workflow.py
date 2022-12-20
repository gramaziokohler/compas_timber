from compas_timber.connections.l_miter import LMiterJoint
from compas_timber.connections.t_butt import TButtJoint
from compas_timber.connections.x_lap import XLapJoint
from compas_timber.utils.compas_extra import intersection_line_line_3D
from compas.geometry import cross_vectors
from compas.geometry import distance_point_point
from compas.geometry import subtract_vectors
from compas.geometry import length_vector, add_vectors, scale_vector, dot_vectors
from compas_timber.parts import Beam

class CollectionDef():
    def __init__(self, objs):
        objs = [_ for _ in objs if _]
        
        self.objs = objs
        self.keys_map = {}
        
        for i,obj in enumerate(objs):
            self.keys_map[i]=obj
    def __str__(self):
        return "Collection with %s items."%len(self.objs)

class JointDefinition():
    joint_types = ['T-Butt', 'L-Miter', 'L-Butt']

    def __init__(self, joint_type, beams):

        if joint_type not in self.joint_types: raise UserWarning("Wrong 'joint_type'. Instead of %s it should be one of the following strings: %s"%(joint_type, self.joint_types))
        beams_clean = [b for b in beams if b.__class__.__name__ == Beam.__name__ ]
        if len(beams_clean)!=2: raise UserWarning("Expected to get two Beams, got %s: %s."%(len(beams_clean),beams))

        self.joint_type = joint_type
        self.beams = beams
    def __str__(self):
        return "JointDef: %s %s"%(self.joint_type, self.beams)
    def __hash__(self):
        return hash(str(self))
    
    def __eq__(self,other):
        return (
            isinstance(other, JointDefinition) and
            self.joint_type == other.joint_type and
            self.beams[0] in other.beams and
            self.beams[1] in other.beams
        )

class FeatureDefinition():
    operations = ['trim']
    def __init__(self, feature_type, feature_shape, beam):

        if feature_type not in self.operations: raise UserWarning("Wrong 'feature_type'. Instead of %s it should be one of the following strings: %s"%(feature_type, self.operations))
        if beam.__class__.__name__ != Beam.__name__ : raise UserWarning("Expected to get a Beam, got %s."%beam)

        self.feature_type=feature_type
        self.beam = beam
        self.feature_shape = feature_shape

    def __str__(self):
        return "FeatureDef: %s %s %s"%(self.feature_type, self.feature_shape, self.beam)

class Attribute():
    def __init__(self,attr_name, attr_value):
        self.name = attr_name
        self.value = attr_value

    def __str__(self):
        return "Attribute %s: %s" % (self.name,self.value)



def guess_joint_topology_2beams(beamA, beamB,  tol=1e-6, max_distance = None):

    if not max_distance: 
        max_distance = beamA.height + beamB.height


    # #check if lines parallel (could be an I-joint)
    # def lines_parallel(line1, line2):
    #     a, b = line1
    #     c, d = line2

    #     ab = subtract_vectors(b, a)
    #     cd = subtract_vectors(d, c)

    #     n = cross_vectors(ab, cd)

    #     # check if lines are parallel
    #     if length_vector(n) < tol: 
    #         return True
    #     else:
    #         return False

    # def contact_points(lineA,lineB):
    #     a1,a2 = lineA
    #     b1,b2 = lineB
    #     for a in [a1,a2]:
    #         for b in [b1,b2]:
    #             if distance_point_point(a,b)<max_distance:
    #                 return a,b
    #     return None

    # if lines_parallel(beamA.centreline, beamB.centreline):
    #     if contact_points(beamA.centreline,beamB.centreline):
    #         #TODO: add a check if the angle between beams is 0 degrees or 180 degrees.  Return None if 0 degrees.
    #         #TODO: replace with 'I' 
    #         return ['L',(beamA, beamB)]

    [pa,ta], [pb,tb] = intersection_line_line_3D(
        beamA.centerline, beamB.centerline, max_distance, True, tol
    )

    if ta == None or tb == None:
        #lines do not intersect within max distance or they are parallel
        return [None, None]


    def is_near_end(t, tol=tol):
        if abs(t) < tol:
            return True  # almost zero
        if abs(1.0 - t) < tol:
            return True  # almost 1
        return False

    xa = is_near_end(ta)
    xb = is_near_end(tb)

    if all([xa, xb]):
        # L-joint (both meeting at ends) TODO: this could also be an I-joint (splice) -> will need to check for angle between beams
        return ["L", (beamA, beamB)]
    elif any([xa, xb]):
        # T-joint (one meeting with the end along the other)
        if xa:
            # A:main, B:cross
            return ["T", (beamA, beamB)]
        if xb:
            # B:main, A:cross
            return ["T", (beamB, beamA)]
    else:
        # X-joint (both meeting somewhere along the line)
        return ["X", (beamA, beamB)]

def set_defaul_joints(
    model, x_default="x-lap", t_default="t-butt", l_default="l-miter"
):
    beams = model.beams
    n = len(beams)

    connectivity = {"L": [], "T": [], "X": []}

    # find what kind of joint topology it looks like based on centrelines
    for i in range(n - 1):
        for j in range(i + 1, n):
            jointtype, beams_pair = guess_joint_topology_2beams(beams[i], beams[j])
            if jointtype:
                connectivity[jointtype].append(beams_pair)

    # Apply default joint types depending on the auto-found connectivity type:

    for beamA, beamB in connectivity["T"]:
        TButtJoint(beamA, beamB, model)

    for beamA, beamB in connectivity["L"]:
        LMiterJoint(beamA, beamB, model)

    for beamA, beamB in connectivity["X"]:
        XLapJoint(beamA, beamB, model)
