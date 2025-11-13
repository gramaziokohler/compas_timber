from compas.data import json_load

from compas_timber.model import TimberModel
from compas_ifc.model import Model

PATH = r"C:\Users\ckasirer\Documents\Projects\COMPAS Timber\sounding_board_2025\demo_v2\multi_wall.json"

model: TimberModel = json_load(PATH)

model.process_joinery()

IFC_PATH = r"C:\Users\ckasirer\Documents\Projects\COMPAS Timber\sounding_board_2025\demo_v2\multi_wall.ifc"


# def join_meshes(meshes):
#     joined_mesh = meshes[0]
#     for mesh in meshes[1:]:
#         joined_mesh.join(mesh)
#     return joined_mesh


ifc_model = Model.template()
storey = ifc_model.building_storeys[0]

# for element in model.beams:
#     beam = ifc_model.create(
#         "IfcBeam",
#         parent=storey,
#         geometry=element.geometry,
#         Name=element.name,
#     )

for slab in model.slabs:
    ifc_wall = ifc_model.create(
        "IfcWall",
        parent=storey,
        geometry=slab.geometry,
        Name=slab.name,
    )
    for beam in slab.name.children:
        ifc_model.create(
            "IfcBeam",
            parent=ifc_wall,
            geometry=beam.geometry,
            Name=beam.name,
        )


ifc_model.unit = "m"
# model.show()
ifc_model.save(IFC_PATH)
