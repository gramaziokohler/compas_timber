from compas.geometry import Point, Line, Frame, Vector, Plane
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.connections import LMiterJoint
from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber._fabrication import Slot

from compas_viewer import Viewer

HEIGHT = 0.16
WIDTH = 0.16

lines = [
    Line(
        Point(x=-15.3434349155, y=-47.6727866999, z=3.19370749185),
        Point(x=-14.4349832900, y=-49.4068049470, z=3.33773536759),
    ),
    Line(
        Point(x=-14.4349832900, y=-49.4068049470, z=3.33773536759),
        Point(x=-13.5265316642, y=-51.1408231946, z=3.49473235078),
    ),
    Line(
        Point(x=-13.5650187581, y=-46.5635415878, z=3.04807177108),
        Point(x=-12.6629397662, y=-48.2941722745, z=3.18185084423),
    ),
    Line(
        Point(x=-12.6629397662, y=-48.2941722745, z=3.18185084423),
        Point(x=-11.7608494658, y=-50.0248246566, z=3.32690606589),
    ),
    Line(
        Point(x=-11.9140586350, y=-45.5337941695, z=2.92210625189),
        Point(x=-11.0216443747, y=-47.2636338857, z=3.04769602051),
    ),
    Line(
        Point(x=-11.0216443747, y=-47.2636338857, z=3.04769602051),
        Point(x=-10.1291963181, y=-48.9935391123, z=3.18328028875),
    ),
    Line(
        Point(x=-15.3434349155, y=-47.6727866999, z=3.19370749185),
        Point(x=-13.5650187581, y=-46.5635415878, z=3.04807177108),
    ),
    Line(
        Point(x=-13.5650187581, y=-46.5635415878, z=3.04807177108),
        Point(x=-11.9140586350, y=-45.5337941695, z=2.92210625189),
    ),
    Line(
        Point(x=-14.4349832900, y=-49.4068049470, z=3.33773536759),
        Point(x=-12.6629397662, y=-48.2941722745, z=3.18185084423),
    ),
    Line(
        Point(x=-12.6629397662, y=-48.2941722745, z=3.18185084423),
        Point(x=-11.0216443747, y=-47.2636338857, z=3.04769602051),
    ),
    Line(
        Point(x=-13.5265316642, y=-51.1408231946, z=3.49473235078),
        Point(x=-11.7608494658, y=-50.0248246566, z=3.32690606589),
    ),
    Line(
        Point(x=-11.7608494658, y=-50.0248246566, z=3.32690606589),
        Point(x=-10.1291963181, y=-48.9935391123, z=3.18328028875),
    ),
]

slot_frame = Frame(
    point=Point(x=-14.368, y=-49.541, z=3.338),
    xaxis=Vector(x=0.464, y=-0.886, z=0.000),
    yaxis=Vector(x=0.000, y=0.000, z=1.000),
)

slot_plane = Plane.from_frame(slot_frame)

model = TimberModel()

for line in lines:
    beam = Beam.from_centerline(line, WIDTH, HEIGHT)
    model.add_beam(beam)

solver = ConnectionSolver()
pairs = solver.find_intersecting_pairs(model.beams, rtree=True)

for pair in pairs:
    beam_a, beam_b = pair
    topo, beam_a, beam_b = solver.find_topology(beam_a, beam_b)
    if topo == JointTopology.TOPO_L:
        LMiterJoint.create(model, beam_a, beam_b)

for b_index, beam in enumerate(model.beams):
    try:
        beam.add_features([Slot.from_plane_and_beam(slot_frame, beam, depth=0.46, thickness=0.10)])
    except ValueError:
        # print(f"could not apply slot to beam #{b_index}")
        pass
    else:
        print(f"slot applied to beam #{b_index}")

viewer = Viewer()
viewer.renderer.camera.position = [-10, -50, 3]
viewer.renderer.camera.pandelta = 0.005
viewer.renderer.camera.target = [-13, -48, 3]

for beam in model.beams:
    viewer.scene.add(beam.geometry)

# viewer.scene.add(slot_plane)

viewer.show()
