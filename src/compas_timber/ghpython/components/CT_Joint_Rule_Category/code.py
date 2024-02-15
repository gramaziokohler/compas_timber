from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper

from compas_timber.ghpython import CategoryRule


def AddParam(name, IO, list = True):
    assert IO in ('Output', 'Input')
    params = [param.NickName for param in getattr(ghenv.Component.Params,IO)]
    if name not in params:
        param = Grasshopper.Kernel.Parameters.Param_GenericObject()
        param.NickName = name + " category"
        param.Name = name
        param.Description = name
        param.Access = Grasshopper.Kernel.GH_ParamAccess.item
        param.Optional = True
        index = getattr(ghenv.Component.Params, IO).Count
        registers = dict(Input  = 'RegisterInputParam'
                        ,Output = 'RegisterOutputParam'
                        )
        getattr(ghenv.Component.Params,registers[IO])(param, index)
        ghenv.Component.Params.OnParametersChanged()
        return param

class DirectJointRule(component):
    def __init__(self):
        self.joint_type = None

    def ClearParams(self):
        while len(ghenv.Component.Params.Input)>1:
            ghenv.Component.Params.UnregisterInputParameter(ghenv.Component.Params.Input[len(ghenv.Component.Params.Input)-1])
        ghenv.Component.Params.OnParametersChanged()
        ghenv.Component.ExpireSolution(True)


    def RunScript(self, JointOptions, *args):
        if not JointOptions:            #if no JointOptions is input
            print("no joint")
            self.ClearParams()
            self.joint_type = None
            return

        if JointOptions.type != self.joint_type:        # if JointOptions changes
            if len(JointOptions.beam_names) != 2:
                self.AddRuntimeMessage(Error, "Component currently only supports joint types with 2 beams.")
            self.ClearParams()
            self.joint_type = JointOptions.type
            for name in JointOptions.beam_names:
                AddParam(name, "Input")

        if len(ghenv.Component.Params.Input) != 3:          # something went wrong and the number of input parameters is wrong
            self.AddRuntimeMessage(Warning, "Input parameter error.")
            return

        if len(args) < 2:
            self.AddRuntimeMessage(Warning, "Input parameters failed to collect data.")
            return
        categories = []
        create_rule = True
        for i in range(len(ghenv.Component.Params.Input)-1):
            if not args[i]:
                self.AddRuntimeMessage(Warning, "Input parameter {} {} failed to collect data.".format(JointOptions.beam_names[i], 'categories'))
                create_rule = False
            else:
                 categories.append(args[i])

        if create_rule:
            return CategoryRule(JointOptions.type, categories[0], categories[1], **JointOptions.kwargs)
