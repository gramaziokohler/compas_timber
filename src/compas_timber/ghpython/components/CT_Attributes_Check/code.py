import math

import Rhino
import Rhino.Geometry as rg
import System
from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.ghpython.ghcomponent_helpers import list_input_valid
from compas_timber.ghpython.rhino_object_name_attributes import get_obj_attributes


class Attributes_Check(component):
    def RunScript(self, ref_obj):
        self.data = []

        list_input_valid(self, ref_obj, "RefObj")

        for obj in ref_obj:
            d = {"refobj": ref_obj, "crv": None, "msg": [], "ok": None, "pln": None, "pt": None}

            crv = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(obj).Geometry
            if not crv:
                continue
            d["crv"] = crv

            # check attributes, get message
            m = self.attributes_checker(obj)
            m = "\n".join(m)
            d["msg"] = m
            d["ok"] = len(m) == 0

            # get the location (point,plane) to display message
            if len(m) > 0:
                t = crv.NormalizedLengthParameter(0.5)[1]
                x = crv.TangentAt(t)
                o = crv.PointAt(t)
                tol = 1e-3
                a = rg.Vector3d.VectorAngle(x, rg.Vector3d(0, 0, 1))
                if a > tol and a < (math.pi - tol):
                    y = rg.Vector3d.CrossProduct(-x, rg.Vector3d(0, 0, 1))
                    p = rg.Plane(o, x, y)
                else:
                    y = rg.Vector3d.CrossProduct(x, rg.Vector3d(0, 1, 0))
                    p = rg.Plane(o, x, y)
                d["pln"] = p
                d["pt"] = o

            self.data.append(d)

    def DrawViewportWires(self, arg):
        if self.Locked:
            return

        colorOK = System.Drawing.Color.FromArgb(255, 0, 150, 100)
        colorBAD = System.Drawing.Color.FromArgb(255, 220, 0, 70)
        colors = [colorBAD, colorOK]

        thick = 5
        for i, d in enumerate(self.data):
            line = d["crv"]
            col = colors[d["ok"]]

            arg.Display.DrawLine(line.PointAtStart, line.PointAtEnd, col, thick)
            if not d["ok"]:
                arg.Display.Draw2dText(d["msg"], col, d["pt"], False, 16)

    def attributes_checker(self, obj):
        msg = []
        attrdict = get_obj_attributes(obj)
        if not attrdict:
            return ["no attributes"]

        if "zvector" in attrdict:
            # check formatting
            z = attrdict["zvector"]
            if (z[0] != "{" or z[-1] != "}") or ("," not in z) or (len(z.split(",")) != 3):
                msg.append("zvector: wrong format: %s" % z)

        else:
            msg.append("zvector: unset")

        if "width" in attrdict:
            w = attrdict["width"]
            try:
                x = float(w)
                if x <= 0.0:
                    msg.append("width: wrong value: %s" % w)
            except Exception:
                msg.append("width: wrong value: %s" % w)
        else:
            msg.append("width: unset")

        if "height" in attrdict:
            h = attrdict["height"]
            try:
                x = float(h)
                if x <= 0.0:
                    msg.append("height: wrong value: %s" % h)
            except Exception:
                msg.append("height: wrong value: %s" % h)
        else:
            msg.append("height: unset")

        if "category" in attrdict:
            pass
        else:
            msg.append("category: unset")
        return msg
