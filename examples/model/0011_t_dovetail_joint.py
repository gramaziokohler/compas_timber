from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Translation
from compas.geometry import Vector
from compas_viewer import Viewer

from compas_timber.connections import TDovetailJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def create_viewer():
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


def create_model():
    """Create a two-beam T-topology model joined with a TDovetailJoint."""
    main_centerline = Line(Point(0, 0, 0), Point(1000, 0, 0))
    main_beam = Beam.from_centerline(main_centerline, width=80, height=100)

    cross_centerline = Line(Point(500, -300, 0), Point(500, 300, 0))
    cross_beam = Beam.from_centerline(cross_centerline, width=80, height=100)

    model = TimberModel()
    model.add_elements([main_beam, cross_beam])

    TDovetailJoint.create(model, main_beam, cross_beam)
    model.process_joinery()

    return model, main_beam, cross_beam


def main():
    model, main_beam, cross_beam = create_model()

    # feature application errors are swallowed into `debug_info` rather than raised, check them here
    for beam in (main_beam, cross_beam):
        for error in beam.debug_info:
            print(f"{beam}: {error.message}")

    viewer = create_viewer()

    for beam in model.beams:
        viewer.scene.add(beam.centerline)

    model.transform(Translation.from_vector(Vector(0, 0, 500)))

    for beam in model.beams:
        viewer.scene.add(beam.geometry)

    viewer.show()


if __name__ == "__main__":
    main()
