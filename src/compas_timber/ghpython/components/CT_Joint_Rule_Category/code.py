from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
import Grasshopper

from compas_timber.ghpython import CategoryRule
from compas_timber.ghpython import manage_dynamic_params


class CategoryJointRule(component):
    def RunScript(self, joint_options, *args):
        if joint_options:
            names = [name + " category" for name in joint_options.beam_names]
        else:
            names = None

        manage_dynamic_params(names, ghenv)

        if not args or not names:  # check that dynamic params generated
            return

        if len(args) != len(names):  # check that dynamic params generated correctly
            self.AddRuntimeMessage(Error, "Input parameter error.")
            return

        create_rule = True
        for i in range(len(names)):
            if not args[i]:
                self.AddRuntimeMessage(
                    Warning, "Input parameter {} {} failed to collect data.".format(names[i], "categories")
                )
                create_rule = False
        if create_rule:
            return CategoryRule(joint_options.type, *args, **joint_options.kwargs)
