from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import project_point_plane
from compas_viewer import Viewer
from compas_timber.elements import Beam

from compas_timber.model import TimberModel
from compas_timber._fabrication import Drilling
from compas_timber.fabrication import BTLx


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


width = 60
height = 120

centerline = Line(Point(x=50.2383355354, y=719.619588434, z=180.0), Point(x=939.792837130, y=262.790529931, z=180.0))

beam = Beam.from_centerline(centerline, width, height)

model = TimberModel()
model.add_beam(beam)

# tilted
# drill_line = Line(
#     Point(x=156.807368849, y=682.533125601, z=180.0), Point(x=156.909094738, y=664.891259740, z=247.788467167)
# )

# tilted other way
drill_line = Line(
    Point(x=126.955522077, y=665.725349607, z=180.0), Point(x=156.909094738, y=664.891259740, z=247.788467167)
)

diameter = 10

drilling = Drilling.from_line_and_beam(drill_line, diameter, beam)

print(f"start_x: {drilling.start_x}, start_y: {drilling.start_y}")
print(f"angle: {drilling.angle}, inclination: {drilling.inclination}")

beam.add_features([drilling])

btlx = BTLx(model)
PATH = r"C:\Users\ckasirer\Documents\Projects\COMPAS Timber\beam_btlx\drilling.btlx"
btlx_gen = BTLx(model)
btlx_gen.process_model()
with open(PATH, "w") as file:
    file.write(btlx_gen.btlx_string())

viewer = create_viewer()
viewer.scene.add(beam.geometry)
viewer.scene.add(drill_line)
# viewer.scene.add(beam.side_as_surface(2))
# viewer.scene.add(Point(x=142.667, y=638.428, z=265.985))
# viewer.scene.add(Point(132.7399768948962, 654.6876592080393, 240.0))
viewer.show()
