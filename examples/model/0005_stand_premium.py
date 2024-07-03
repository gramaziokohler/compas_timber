import os
from collections import defaultdict

from compas.data import json_load
from compas.geometry import Vector
from compas_viewer.viewer import Viewer
from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.elements import Wall
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import TButtJoint
from compas_timber.connections import LButtJoint
from compas_timber.connections import JointTopology
from compas.geometry import oriented_bounding_box_numpy
from compas.geometry import Box


HERE = os.path.dirname(__file__)
LINES = os.path.join(HERE, "stand_premium.json")


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


def get_group_name(beam, model):
    if beam.attributes["category"] in model._groups:
        return beam.attributes["category"]
    prefix = beam.attributes["category"].split("_")[0]
    for group_name in model._groups.keys():
        if group_name.startswith(prefix):
            return group_name


# Load centerlines from file
lines = json_load(LINES)

model = TimberModel()

# Add beams to model
CROSS_SQUARE = (120, 120)
CROSS_TALL = (120, 60)
NORMAL_VERTICALS = Vector(0, 1, 0)
NORMAL_REST = Vector(0, 0, 1)

beams_cats = lines["cats"]
walls = lines["walls"]

################### Walls ######################

# create and add beams
for wall_name, box in walls.items():
    wall = Wall.from_box(box)
    wall.name = wall_name
    model.add_wall(wall)

print(model._groups)


################### Hierarchy ######################

# # Create the beams with the right cross section depending on their category
# # Assign normal to the beams whose centerlines are aligned with the zaxis
for category, lines in beams_cats.items():
    for line in lines:
        if category in ["wall_frame", "roof_frame", "floor_frame", "support_right", "support_left", "window"]:
            height, width = CROSS_SQUARE
        else:
            height, width = CROSS_TALL
        normal = NORMAL_VERTICALS if category == "wall_studs" else None
        beam = Beam.from_centerline(centerline=line, height=height, width=width, z_vector=normal)
        beam.attributes["category"] = category
        group_name = get_group_name(beam, model)
        model.add_beam(beam, group_name=group_name)

################### Interactions ######################

# create topology to joint type mapping
topo_connection = {JointTopology.TOPO_L: LButtJoint, JointTopology.TOPO_T: TButtJoint}

# find neighboring beams
solver = ConnectionSolver()
beam_pairs = solver.find_intersecting_pairs(model.beams, rtree=True)

for pair in beam_pairs:
    beam_a, beam_b = pair

    # find topology and reorder beams according to roles if needed based on found topology
    topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    # join beams accorgind to topology to connection type mapping
    joint_cls = topo_connection.get(topo, None)
    if joint_cls is not None:
        joint_cls.create(model, beam_a, beam_b)

################### Visualization ######################

# # setup the viewer
viewer = create_viewer()

# draw centerline
# for beam in model.beams:
#     viewer.scene.add(beam.centerline)

# # draw geometry (with features)
for node in model.tree.traverse():
    print(f"node:{node}")
    if node.name == "root":
        continue
    if node.is_leaf:
        viewer.scene.add(node.element.geometry)
    else:
        element = node.attributes["element"]
viewer.scene.add(element.geometry)

# for element in elements:
#     viewer.scene.add(element.geometry)

# for beam in model.beams:
#     viewer.scene.add(beam.geometry)
# for vertex in beam.geometry.vertices:
#     viewer.scene.add(vertex.point)

for wall in model.walls:
    viewer.scene.add(wall.geometry)


viewer.show()

print(str(model.graph))
print(str(model.tree))
