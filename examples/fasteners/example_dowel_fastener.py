from compas.colors import Color
from compas.geometry import Line
from compas_threejs.materials import Material
from compas_threejs.viewer import Viewer

from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fasteners import DowelFastener
from compas_timber.fasteners.anchor import AnchorKind
from compas_timber.model import TimberModel

cross_beam = Beam.from_centerline(Line([0, 0, 0], [2, 0, 0]), width=0.05, height=0.05)
main_beam = Beam.from_centerline(Line([1, 0, 0], [0.75, 0.5, 0.25]), width=0.05, height=0.05)
main_beam.frame.yaxis = [0, 0, 1]

model = TimberModel()
model.add_elements([cross_beam, main_beam])


joint = TButtJoint.create(model, main_beam, cross_beam, mill_depth=0.01, force_pocket=True)


fastener = DowelFastener(diameter=0.02, length=0.1, angle_x=None, angle_y=None)

anchors = joint.fastener_anchors.of_kind(AnchorKind.AXIS)
fastener.bind(anchors)

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
    print(fastener.geometry)
    viz.add_geometries(fastener.geometry, mat)


for anchor in joint.fastener_anchors:
    viz.add_geometry(anchor.frame)

viz.start()
