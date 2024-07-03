from compas.geometry import Vector
from compas.geometry import Frame
from compas_viewer.viewer import Viewer
from compas_timber.model import TimberModel
from compas_timber.elements import Wall


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


model = TimberModel()

# Add beams to model
CROSS_SQUARE = (120, 120)
CROSS_TALL = (120, 60)
NORMAL_VERTICALS = Vector(0, 1, 0)
NORMAL_REST = Vector(0, 0, 1)

wall_frame = Frame.worldXY()
model = TimberModel()
model.add_wall(Wall(wall_frame, 3000, 140, 2000))

# setup the viewer
viewer = create_viewer()

wall = model.walls[0]

# draw centerline
viewer.scene.add(wall.origin)
viewer.scene.add(wall.baseline)
viewer.scene.add(wall.geometry)

viewer.show()
