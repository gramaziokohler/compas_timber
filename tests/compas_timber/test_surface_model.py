from compas_timber.design import SurfaceModel
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import Point


def test_surface_model():
    outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 625,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
    model = outline_model.create_model()
    model.process_joinery()

    assert len(outline_model.headers) == 1
    assert len(outline_model.sills) == 1
    assert len(outline_model.edge_studs) == 2
    assert len(outline_model.plates) == 2
    assert len(list(outline_model.plate_elements)) == 2
    assert len(list(model.beams)) == 19
    assert len(list(model.plates)) == 2
    for element in model.elements():
        assert len(element.features) == 2
    assert len(model.joints) == 32


def test_surface_model_stud_spacing():
    outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 1250,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
    model = outline_model.create_model()
    model.process_joinery()

    assert len(outline_model.headers) == 1
    assert len(outline_model.sills) == 1
    assert len(outline_model.edge_studs) == 2
    assert len(outline_model.plates) == 2
    assert len(list(outline_model.plate_elements)) == 2
    assert len(list(model.beams)) == 14
    assert len(list(model.plates)) == 2
    for element in model.elements():
        assert len(element.features) == 2
    assert len(model.joints) == 22


def test_surface_model_with_door():
    outline = outline = Polyline([Point(0, 0, 0),Point(3000, 0, 0),Point(3000, 0, 2000),Point(4000, 0, 2000),Point(4000, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 625,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
    model = outline_model.create_model()
    model.process_joinery()

    assert len(outline_model.headers) == 2
    assert len(outline_model.sills) == 1
    assert len(outline_model.edge_studs) == 2
    assert len(outline_model.plates) == 3
    assert len(list(outline_model.plate_elements)) == 2
    assert len(list(model.beams)) == 25
    assert len(list(model.plates)) == 2
    for element in model.elements():
        assert len(element.features) == 2
    assert len(model.joints) == 40


def test_surface_model_no_lintel_posts():
    outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 1250,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0, lintel_posts=False)
    model = outline_model.create_model()
    model.process_joinery()

    assert len(outline_model.headers) == 1
    assert len(outline_model.sills) == 1
    assert len(outline_model.edge_studs) == 2
    assert len(outline_model.plates) == 2
    assert len(list(outline_model.plate_elements)) == 2
    assert len(list(model.beams)) == 12
    assert len(list(model.plates)) == 2
    for element in model.elements():
        assert len(element.features) == 2
    assert len(model.joints) == 20


def test_surface_model_reverse_curves():
    outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    outline = Polyline(outline[::-1])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 625,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
    model = outline_model.create_model()
    model.process_joinery()
    assert len(list(model.elements())) == 21
    assert len(model.joints) == 32

    outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    inlines = Polyline(inlines[::-1])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 625,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
    model = outline_model.create_model()
    model.process_joinery()
    assert len(list(model.elements())) == 21
    assert len(model.joints) == 32


    outline = Polyline([Point(0, 0, 0), Point(5000, 0, 0), Point(5000, 0, 2500), Point(0, 0, 2500), Point(0, 0, 0)])
    inlines = Polyline([Point(800, 0, 700), Point(2000, 0, 700), Point(2000, 0, 2000), Point(800, 0, 2000), Point(800, 0, 700)])
    outline = Polyline(outline[::-1])
    inlines = Polyline(inlines[::-1])
    outline_model = SurfaceModel(outline,  -Vector.Yaxis(),[inlines], 625,60,120,Vector.Zaxis(), sheeting_inside = 40.0, sheeting_outside = 20.0)
    model = outline_model.create_model()
    model.process_joinery()
    assert len(list(model.elements())) == 21
    assert len(model.joints) == 32
