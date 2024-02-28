from ghpythonlib.componentbase import executingcomponent as component
import Grasshopper, GhPython
import System
import Rhino
import rhinoscriptsyntax as rs

class BeamDimensionContainer(object):
    def __init__(self, plate, edge_stud, king_stud, jack_stud, stud, sill, header):
        self.dims = {
                "plate": (plate[0]if not None, plate[1]),
                "edge_stud": (edge_stud[0], edge_stud[1]),
                "king_stud": (king_stud[0], king_stud[1]),
                "jack_stud": (jack_stud[0], jack_stud[1]),
                "stud": (stud[0], stud[1]),
                "sill": (sill[0], sill[1]),
                "header": (header[0], header[1])
            }


def parse_input(input):
    if input:
        if len(input) == 1 or isinstance(input, float) or isinstance(input, int):
            return (input, None)
        if len(input) == 2:
            return (input[0], input[1])
        else:
            raise ValueError("Input must be a single value or a list of two values.")


class BeamDimensions(component):
    def RunScript(self, *args):
        dim_args = []
        for arg in args:
            arg = parse_input(arg)
            dim_args.append(arg)

        dims = BeamDimensionContainer(*dim_args)
        return dims
