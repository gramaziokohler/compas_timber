import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

from compas_timber.utils.rhinoscript import cmd_string_options

if "manual_joints" in sc.sticky.keys():
    if len(sc.sticky["manual_joints"]) == 0:
        print("No joints defined yet.")
    else:
        print("Clear joint type")
        beamA = rs.GetObject(
            "Select the centreline of the first beam...", 4, False, False
        )
        beamB = rs.GetObject(
            "Select the centreline of the second beam...", 4, False, False
        )

        for item in sc.sticky["manual_joints"][:]:
            a, b, t = item
            if a in [beamA, beamB] and b in [beamA, beamB]:
                sc.sticky["manual_joints"].remove(item)
                print("Unset the %s type of joint for these two beams." % t)
