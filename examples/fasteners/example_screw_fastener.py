from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Line
from compas_threejs.materials import Material
from compas_threejs.viewer import Viewer

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import Screw
from compas_timber.fasteners import ScrewFastenerSystem
from compas_timber.fasteners.anchor import AnchorKind
from compas_timber.model import TimberModel

cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [0.75, 0.5, 0.25]), width=0.05, height=0.05)
main_beam.frame.yaxis = [0, 0, 1]

model = TimberModel()
model.add_elements([cross_beam, main_beam])


joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True)


# WHAT: a joint-agnostic screw fastener. Screws describe a reusable pattern: each screw's own placement frame is an
# offset within the group, so a fastener can bundle several screws that all get placed together at every anchor.
#
# Here the pattern has two screws, offset side by side, to compare the `precise` flag:
# - `precise=False` (the default): just the cylindrical shank, cheap to compute.
# - `precise=True`: the shank unioned with a conical countersunk head into a single Brep.
screw_simple = Screw(diameter=0.008, length=0.12, placement_frame=Frame([-0.015, 0, 0], [1, 0, 0], [0, 1, 0]))
screw_precise = Screw(diameter=0.008, length=0.12, precise=True, placement_frame=Frame([0.015, 0, 0], [1, 0, 0], [0, 1, 0]))

system = ScrewFastenerSystem([screw_simple, screw_precise])

# WHERE: the joint publishes its attachment anchors; the system binds to the ones it accepts (AXIS or POINT)
anchors = joint.fastener_anchors.of_kind(AnchorKind.AXIS)
fastener = system.bind(anchors)

model.add_fastener(fastener, joint.beams)
model.process_joinery()
model.process_fasteners()


viz = Viewer()
viz.show_edges = True
viz.camera_position = [1, -1, 1]

mat = Material(color=Color.brown(), opacity=0.5, transparent=True)
for beam in model.beams:
    viz.add_geometry(beam.geometry, mat)


mat = Material(color=Color.grey(), opacity=0.5, transparent=True)
for fastener in model.fasteners:
    viz.add_geometries(fastener.geometry, mat)


for anchor in joint.fastener_anchors:
    viz.add_geometry(anchor.frame)

viz.start()
