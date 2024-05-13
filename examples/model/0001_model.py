import os

from compas.data import json_load
from compas_viewer.viewer import Viewer

from compas_timber.model import TimberModel
from compas_timber.elements import Beam
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint


HERE = os.path.dirname(__file__)
VIEWER_CONFIG = os.path.join(HERE, 'viewer_config')
LINES = os.path.join(HERE, 'lines.json')

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
TButtJoint.create(model, beams[2], beams[1])


# Assign joints - Frame - Inner
TButtJoint.create(model, beams[1], beams[0])
TButtJoint.create(model, beams[1], beams[3])
TButtJoint.create(model, beams[2], beams[4])

# draw inflated centerlines
viewer = Viewer(configpath=VIEWER_CONFIG)

# for beam in model.beams:
#     viewer.add(beam.shape)

# draw blanks (including joinery extensions)
# for beam in model.beams:
#     viewer.add(beam.blank)

# draw geometry (with features)
for beam in model.beams:
    viewer.add(beam.geometry)


viewer.show()
