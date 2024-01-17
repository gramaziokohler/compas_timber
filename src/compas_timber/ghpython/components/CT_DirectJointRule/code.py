
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.ghpython import JointDefinition
from compas_timber.ghpython import DirectRule



class DirectJointRule(component):
    def RunScript(self, JointOptions, MainBeam, SecondaryBeam):
        if not MainBeam:
            self.AddRuntimeMessage(Warning, "Input parameter MainBeams failed to collect data.")
        if not SecondaryBeam:
            self.AddRuntimeMessage(Warning, "Input parameter CrossBeams failed to collect data.")
        if not (MainBeam and SecondaryBeam):
            return
        if not isinstance(MainBeam, list):
            MainBeam = [MainBeam]
        if not isinstance(SecondaryBeam, list):
            SecondaryBeam = [SecondaryBeam]
        if len(MainBeam) != len(SecondaryBeam):
            self.AddRuntimeMessage(Error, "Number of items in MainBeams and CrossBeams must match!")
            return


        for main, secondary in zip(MainBeam, SecondaryBeam):
            topology, _, _ = ConnectionSolver().find_topology(main, secondary)
            if topology != JointOptions.type.SUPPORTED_TOPOLOGY:
                self.AddRuntimeMessage(
                    Warning,
                    "Beams meet with topology: {} which does not agree with joint of type: {}".format(
                        JointTopology.get_name(topology), JointOptions.type.__name__
                    ),
                )
                continue
            Rule = DirectRule(JointOptions.type, [secondary, main], **JointOptions.kwargs)
        return Rule

