from compas_timber.design import SurfaceModel
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import Point
from compas.scene import Scene



outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])

inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])

outline = Polyline(outline[::-1])
inlines = Polyline(inlines[::-1])

outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 625,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
model = outline_model.create_model()

model.process_joinery()
scene = Scene()

for element in model.elements():
    scene.add(element.geometry)

a = scene.draw()
b = model

