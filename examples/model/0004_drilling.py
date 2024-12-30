import os

from compas.geometry import Line
from compas.geometry import Point
from compas_viewer import Viewer
from compas_timber.elements import Beam

from compas_timber.model import TimberModel
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import BTLxWriter

HERE = os.path.dirname(__file__)


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

centerline = Line(
    Point(x=17.2361412989, y=36.4787607210, z=0.0), Point(x=1484.82372687, y=473.845866212, z=224.447551130)
)

beam = Beam.from_centerline(centerline, width, height)

model = TimberModel()
model.add_element(beam)

drill_lines = [
    Line(
        Point(x=126.521643610, y=122.890857338, z=19.6714602873),
        Point(x=165.200858581, y=26.7317879006, z=19.6714602873),
    ),
    Line(
        Point(x=126.521643610, y=122.890857338, z=50.8028514283),
        Point(x=165.200858581, y=26.7317879006, z=50.8028514283),
    ),
    Line(
        Point(x=55.4457899896, y=97.4134493808, z=35.0129732904),
        Point(x=94.1250049601, y=1.25437994317, z=35.0129732904),
    ),
    Line(
        Point(x=93.4694427443, y=97.4134493808, z=35.0129732904),
        Point(x=132.148657715, y=1.25437994317, z=60.8540237143),
    ),
    Line(Point(x=55.4457899896, y=97.4134493808, z=-10.4421113974), Point(x=94.1250049601, y=1.25437994317, z=0.0)),
]

features = []
diameter = 10
for d_line in drill_lines:
    features.append(Drilling.from_line_and_beam(d_line, diameter, beam))


beam.add_features(features)

btlx = BTLxWriter(model)
PATH = os.path.join(HERE, "drilling.btlx")
btlx.write(model, PATH)
viewer = create_viewer()
viewer.scene.add(beam.geometry)
viewer.show()
