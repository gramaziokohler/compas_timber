import compas
from compas.geometry import Line
from .btlx import BTLx

def get_btlx_string(assembly_json):
    """
    the following method is used to get the btlx string in grasshopper
    """
    assembly = compas.json_loads(assembly_json)
    btlx_ins = BTLx(assembly)
    # edges = []
    # for part in btlx_ins.parts:
    #     for tuple in part.blank_geometry.edges:
    #         edges.append(Line(part.blank_geometry.points[tuple[0]], part.blank_geometry.points[tuple[1]]))
    return str(btlx_ins)
