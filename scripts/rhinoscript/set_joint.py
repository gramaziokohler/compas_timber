import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

from compas_timber.utils.compas_extra import intersection_line_line_3D

# sc.sticky['manual_joints']=[ ] #list of [centrelineA_guid, centrelineB_guid, joint_type]
if "manual_joints" not in sc.sticky.keys():
    sc.sticky["manual_joints"] = []

tol = 1e-6


def detect_connection_topology(centrelineA_guid, centrelineB_guid, max_distance=0.0, tol=tol):
    centrelineA = rs.coerceline(centrelineA_guid)
    centrelineB = rs.coerceline(centrelineB_guid)

    def __is_near_end(t, tol=tol):
        if abs(t) < tol:
            return True  # almost zero
        if abs(1.0 - t) < tol:
            return True  # almost 1
        return False

    result = ()

    tA, tB = intersection_line_line_3D(centrelineA, centrelineB, max_distance, True, True, tol)

    if tA == None or tB == None:
        return None
    else:
        xA = __is_near_end(tA)
        xB = __is_near_end(tB)
        if all([xA, xB]):
            # L-joint (meeting at ends)
            result = ("L", [centrelineA_guid, centrelineB_guid], [tA, tB])
        elif not any([xA, xB]):
            # X-joint (meeting somewhere along the line)
            result = ("X", [centrelineA_guid, centrelineB_guid], [tA, tB])
        else:
            # T-joint (one meeting with the end along the other)
            if xA:
                # j:main, i:cross
                result = ("T", [centrelineA_guid, centrelineB_guid], [tA, tB])
            if xB:
                # j:main, i:cross
                result = ("T", [centrelineB_guid, centrelineA_guid], [tB, tA])
    return result


def cmd_string_options(message="Choose:", oplist=["Option1", "Option2"], default_index=0):
    """
    message: [str] prompt to the user
    oplist: [str] list of options to display
    default_index : [int] index of the element in the oplist which should be the default option

    returns: [str] the selected or default option, None on fail
    """

    gs = Rhino.Input.Custom.GetOption()
    gs.SetCommandPrompt(message)
    for op in oplist:
        gs.AddOption(op)
    gs.SetDefaultString(oplist[default_index])
    gs.AcceptNothing(True)

    while True:
        result = gs.Get()
        if result == Rhino.Input.GetResult.Cancel:
            return None
        if gs.GotDefault():
            return oplist[default_index]
        else:
            return gs.Option().EnglishName


def already_there(beamA, beamB, joint_type):
    for a, b, t in sc.sticky["manual_joints"][:]:
        if a in [beamA, beamB] and b in [beamA, beamB]:
            if t == joint_type:
                print("This joint type is already set.")
                return True
            else:
                print("These beams are already set with a %s joint." % t)
                return True
    return False


def set_T_butt_joint(mainbeam, crossbeam):
    if not already_there(mainbeam, crossbeam, "T-Butt"):
        sc.sticky["manual_joints"].append([mainbeam, crossbeam, "T-Butt"])


def set_T_lap_joint(mainbeam, otherbeam):
    if not already_there(mainbeam, otherbeam, "T-Lap"):
        sc.sticky["manual_joints"].append([mainbeam, otherbeam, "T-Lap"])


def set_T_mortisetenon_joint(mainbeam, otherbeam):
    sc.sticky["manual_joints"].append([mainbeam, otherbeam, "T-MortiseTenon"])


if __name__ == "__main__":
    # object filters https://developer.rhino3d.com/api/rhinoscript/selection_methods/getobject.htm
    print("Set the joint type...")
    LineA_guid = rs.GetObject("Select the centreline of the first beam...", 4, False, False)
    LineB_guid = rs.GetObject("Select the centreline of the second beam...", 4, False, False)

    rs.SelectObjects([LineA_guid, LineB_guid])

    max_distance = rs.GetReal("Maximum allowed distance between lines...", 1e-3, 0, None)
    if not max_distance:
        max_distance = tol
    connecting = detect_connection_topology(LineA_guid, LineB_guid, max_distance)
    if not connecting:
        print("These centreline do not intersect... aborting! (Try increasing the max_distance next time)")
    else:
        joint_topo, [mainbeam, otherbeam], [tA, tB] = connecting
        print("This is a %s type of joint." % joint_topo)

        if joint_topo == "T":
            joint_type = cmd_string_options("Select joint type:..", ["Butt", "Lap", "Mortise-Tenon"], 0)
            if joint_type == "Butt":
                set_T_butt_joint(mainbeam, otherbeam)
            if joint_type == "Lap":
                set_T_lap_joint(mainbeam, otherbeam)
            if joint_type == "Mortise-Tenon":
                set_T_mortisetenon_joint(mainbeam, otherbeam)
        elif joint_topo == "L":
            joint_type = cmd_string_options("Select joint type:...", ["Butt", "Lap", "Miter", "Bridle"], 0)
        elif joint_topo == "X":
            joint_type = cmd_string_options("Select joint type:...", ["Lap", "Smth else"], 0)
        elif joint_topo == "I":
            joint_type = None

        # print("The %s-%s joint was set."%(joint_topo,joint_type))
        print(sc.sticky)
