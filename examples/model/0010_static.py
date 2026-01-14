import os

import compas_fea2
from compas.data import json_load
from compas.geometry import Frame
from compas.geometry import Plane
from compas_fea2.model import Model
from compas_fea2.model import Part
from compas_fea2.model import RectangularSection
from compas_fea2.model import Timber
from compas_fea2.problem import Problem
from compas_fea2.problem import StaticStep
from compas_fea2.results import DisplacementFieldResults

import compas_timber
from compas_timber.model import TimberModel

compas_fea2.set_backend("abaqus")


PATH = os.path.join(compas_timber.DATA, "static", "model.json")

timber_model: TimberModel = json_load(PATH)

HERE = os.path.dirname(__file__)
TEMP = os.path.join(HERE, "_temp")

lines = []
for beam in timber_model.beams:
    lines.extend(beam.attributes["attributes"]["structural_centerlines"])


material = Timber.C14()
section = RectangularSection(w=60, h=80, material=material)

# NOTE: this seems to not properly connect all the segments together
# we'd likely have to implement our own `from_compas_lines` to have more control on elements and nodes
part = Part.from_compas_lines(lines, section=section)

model = Model()

model.add_part(part)

# This is just the XY plane at the lowest point of the reciprocal frame
floor = Frame([-1589.09, 4519.88, 1869.43], [1, 0, 0], [0, 1, 0])
model.add_fix_bc(part.find_nodes_on_plane(Plane.from_frame(floor)))

problem = model.add_problem(Problem("timber_problem"))

# TODO: we are likely missing some loads here...
step = StaticStep()

problem.add_step(step)

# Apply 1 neuton of force in z direction to all nodes
step.add_uniform_forcefield(part.nodes, z=1.0)

step.add_field_outputs([DisplacementFieldResults()])

problem.analyse_and_extract(TEMP)
