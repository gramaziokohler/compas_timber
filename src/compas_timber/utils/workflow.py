from compas_timber.utils.compas_extra import intersection_line_line_3D
from compas_timber.connections.t_butt import TButtJoint
from compas_timber.connections.l_miter import LMiterJoint
from compas_timber.connections.x_lap import XLapJoint


def guess_joint_topology_2beams(beamA, beamB, tol = 1e-6):

    max_distance = beamA.height + beamB.height
    
    ti, tj = intersection_line_line_3D(beamA.centreline, beamB.centreline, max_distance, True, True, tol)

    def is_near_end(t, tol=tol):
        if abs(t) < tol:
            return True  # almost zero
        if abs(1.0-t) < tol:
            return True  # almost 1
        return False

    if ti == None or tj == None:
        return [None, None]

    xi = is_near_end(ti)
    xj = is_near_end(tj)

    if all([xi, xj]):
        # L-joint (meeting at ends) TODO: this could also be an I-joint (splice) -> will need to check for angle between beams
        return ['L', (beamA, beamB)]
    elif not any([xi, xj]):
        # X-joint (meeting somewhere along the line)
        return ['X', (beamA, beamB)]
    else:
        # T-joint (one meeting with the end along the other)
        if xi:
            # A:main, B:cross
            return ['T', (beamA, beamB)]
        if xj:
            # B:main, A:cross
            return ['T', (beamB, beamA)]

def set_defaul_joints(model, x_default='x-lap', t_default='t-butt', l_default='l-miter'):
    beams = model.beams
    n = len(beams)

    connectivity = {
    'L':[],
    'T':[],
    'X':[]
    }

    # find what kind of joint topology it looks like based on centerlines
    for i in range(n-1):
        for j in range(i+1,n):
            jointtype, beams_pair = guess_joint_topology_2beams(beams[i], beams[j])
            if jointtype:
                connectivity[jointtype].append(beams_pair)


    #Apply default joint types depending on the auto-found connectivity type:

    for beamA, beamB in connectivity['T']:
        TButtJoint(beamA, beamB, model)

    for beamA, beamB in connectivity['L']:
        LMiterJoint(beamA, beamB, model)

    for beamA, beamB in connectivity['X']:
        XLapJoint(beamA, beamB, model)