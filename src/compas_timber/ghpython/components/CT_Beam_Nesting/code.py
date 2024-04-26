from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path
from compas_timber.planning import Nester


class NestingComponent(component):

    def RunScript(self, assembly, stock_length, tolerance=1, iterations=10):

        if not assembly:
            self.AddRuntimeMessage(Warning, "input Assembly failed to collect data")
            return
        if not stock_length:
            self.AddRuntimeMessage(Warning, "input Stock Length failed to collect data")
            return

        nester = Nester()
        nesting_dict = nester.get_bins(assembly.beams, stock_length, tolerance, iterations)

        data_tree = DataTree[object]()
        for key, value in nesting_dict.items():
            path = GH_Path(int(key))
            data_tree.AddRange(value, path)

        info = []
        info.append("total length: {:.2f}".format(nester.total_length))
        info.append("bin count = {0}".format(len(nesting_dict.items())))
        info.append("cutoff waste = {:.2f}".format(nester.total_space(nesting_dict)))

        beam_list_out = []
        for val in nesting_dict.values():
            beam_list_out.extend(val)

        if set(beam_list_out) != set(assembly.beams):
            self.AddRuntimeMessage(Error, "beams inputs and outputs dont match")

        return data_tree, info
