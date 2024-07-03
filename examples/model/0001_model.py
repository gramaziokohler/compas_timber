import os

from compas.data import json_load
from compas_viewer.viewer import Viewer

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import THalfLapJoint


HERE = os.path.dirname(__file__)
LINES = os.path.join(HERE, "lines.json")


def create_viewer():
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
HEIGHT = 120
WIDTH = 60
for line in lines:
    model.add_beam(Beam.from_centerline(centerline=line, height=HEIGHT, width=WIDTH))

beams = model.beams

# Assign joints - Frame - Frame
LMiterJoint.create(model, beams[5], beams[3])
LMiterJoint.create(model, beams[3], beams[4])
LMiterJoint.create(model, beams[4], beams[0])
LMiterJoint.create(model, beams[0], beams[5])

# Assign joints - Inner - Inner
THalfLapJoint.create(model, beams[2], beams[1])


# Assign joints - Frame - Inner
TButtJoint.create(model, beams[1], beams[0])
TButtJoint.create(model, beams[1], beams[3])
TButtJoint.create(model, beams[2], beams[4])

viewer = create_viewer()

for beam in model.beams:
    viewer.scene.add(beam.centerline)

# draw geometry (with features)
for beam in model.beams:
    viewer.scene.add(beam.geometry)


viewer.show()
