from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.assembly import TimberAssembly


class Assembly(component):

    def RunScript(self, beams, joints, features):
        assembly = TimberAssembly()
        if beams:
            for beam in beams:
                assembly.add_beam(beam)

        if joints:
            for joint in joints:
                joint.joint_type.create(assembly, *joint.beams)

        if features:
            pass

        return assembly
