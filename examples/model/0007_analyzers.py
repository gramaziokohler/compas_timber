import os

from compas.colors import Color
from compas.geometry import KDTree
from compas.geometry import Line
from compas.geometry import Point
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.connections import JointTopology
from compas_timber.connections import TripletAnalyzer
from compas_timber.elements import Beam
from compas_timber.model import TimberModel

HERE = os.path.dirname(__file__)
LINES = os.path.join(HERE, "stand.json")


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 0.05
    viewer.renderer.rendermode = "ghosted"
    return viewer


def main():
    # Load centerlines from file
    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=330.0, y=350.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=500.0, y=0.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=220.0, y=170.0, z=-120.0)),
    ]

    model = TimberModel()

    height, width = (12, 6)

    for line in lines:
        beam = Beam.from_centerline(centerline=line, height=height, width=width)
        model.add_element(beam)

    # pairs of adjacent beams are connected by GenericJoint instances
    model.connect_adjacent_beams()

    # setup the viewer
    viewer = create_viewer()

    for joint in model.joints:
        #     # viewer.scene.add(joint.location)
        topo_name = JointTopology.get_name(joint.topology).split("_")[-1]
        viewer.scene.add(Tag(text=topo_name, position=joint.location, height=40, color=Color.blue()))

    # draw centerline
    for beam in model.beams:
        viewer.scene.add(beam.centerline)
        viewer.scene.add(beam.geometry)

    anazlyzer = TripletAnalyzer(model)
    clusters = anazlyzer.find()

    for cluster in clusters:
        viewer.scene.add(cluster[0].location, pointsize=50, pointcolor=Color.red())
        print([j.location for j in cluster])
        print("==========================")

    viewer.show()


if __name__ == "__main__":
    main()
