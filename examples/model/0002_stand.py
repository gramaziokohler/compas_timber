import os

from compas.data import json_load
from compas.geometry import Vector
from compas_viewer.viewer import Viewer
from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import TButtJoint
from compas_timber.connections import LButtJoint
from compas_timber.connections import JointTopology
from compas.data import json_dump


HERE = os.path.dirname(__file__)
LINES = os.path.join(HERE, "stand.json")


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


# Load centerlines from file
lines = json_load(LINES)

model = TimberModel()

# Add beams to model
CROSS_SQUARE = (120, 120)
CROSS_TALL = (120, 60)
NORMAL_VERTICALS = Vector(0, 1, 0)
NORMAL_REST = Vector(0, 0, 1)

# Create the beams with the right cross section depending on their category
# Assign normal to the beams whose centerlines are aligned with the zaxis
for category, lines in lines.items():
    for line in lines:
        if category in ["main", "support", "window"]:
            height, width = CROSS_SQUARE
        else:
            height, width = CROSS_TALL
        normal = NORMAL_VERTICALS if category == "verticals" else None
        beam = Beam.from_centerline(centerline=line, height=height, width=width, z_vector=normal)
        beam.attributes["category"] = category
        beam.name = category
        model.add_element(beam)

# analyze connections and create joint candidates
model.connect_adjacent_beams()

# create joints for L and T connections
for candidate in model.joint_candidates:
    beam_a, beam_b = candidate.elements
    if candidate.topology == JointTopology.TOPO_L:
        LButtJoint.create(model, beam_a, beam_b)
    elif candidate.topology == JointTopology.TOPO_T:
        TButtJoint.create(model, beam_a, beam_b)

model.process_joinery()

# setup the viewer
viewer = create_viewer()

# draw centerline
for beam in model.beams:
    viewer.scene.add(beam.centerline)

# draw geometry (with features)
for beam in model.beams:
    viewer.scene.add(beam.geometry)

viewer.show()
