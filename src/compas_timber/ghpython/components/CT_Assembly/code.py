from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.assembly import TimberAssembly


class Assembly(component):

    def RunScript(self, beams, joints, features):
        assembly = TimberAssembly()
        if beams:
            beams = [b for b in beams if b is not None]
            for beam in beams:
                beam.clear_features()  # since we're editing the beams
                assembly.add_beam(beam)

        if joints:
            joints = [j for j in joints if j is not None]
            for joint in joints:
                joint.joint_type.create(assembly, *joint.beams)

        if features:
            features = [f for f in features if f is not None]
            for f_def in features:
                for beam in f_def.beams:
                    print(beam.features)
                    beam.add_feature(f_def.feature)

        return assembly
