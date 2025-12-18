# r: compas_timber>=1.0.2
# flake8: noqa

"""Creates a BTLx MachiningLimits object from boolean inputs for each face limit."""

import Grasshopper
import Rhino

from compas_timber.fabrication import MachiningLimits


class BTLxMachiningLimits(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, face_limited_start: bool, face_limited_end: bool, face_limited_front: bool, face_limited_back: bool, face_limited_top: bool, face_limited_bottom: bool):
        # provide default value
        inputs = [
            face_limited_start,
            face_limited_end,
            face_limited_front,
            face_limited_back,
            face_limited_top,
            face_limited_bottom,
        ]

        for i in range(len(inputs)):
            if inputs[i] is None:
                inputs[i] = True

        (
            face_limited_start,
            face_limited_end,
            face_limited_front,
            face_limited_back,
            face_limited_top,
            face_limited_bottom,
        ) = inputs

        # get MachiningLimits object
        machining_limits = MachiningLimits()
        machining_limits.face_limited_start = face_limited_start
        machining_limits.face_limited_end = face_limited_end
        machining_limits.face_limited_front = face_limited_front
        machining_limits.face_limited_back = face_limited_back
        machining_limits.face_limited_top = face_limited_top
        machining_limits.face_limited_bottom = face_limited_bottom
        return machining_limits
