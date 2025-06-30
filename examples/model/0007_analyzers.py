import random

from compas.colors import Color
from compas.colors import ColorMap
from compas.geometry import Line
from compas.geometry import Point
from compas.tolerance import Tolerance
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.connections import JointTopology
from compas_timber.connections import MaxNCompositeAnalyzer
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 0.05
    viewer.renderer.rendermode = "ghosted"
    return viewer


def create_color_map(keys):
    # map cluster sizes to random colors which are hopefully visually distinct
    cmap = ColorMap.from_palette("imola")
    n = len(keys)
    values = [i / max(n - 1, 1) for i in range(n)]
    random.shuffle(values)
    return {key: cmap(val) for key, val in zip(keys, values)}


def main():
    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=330.0, y=350.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=500.0, y=0.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=220.0, y=170.0, z=-120.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=90.0, y=-220.0, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=0.0, y=220.0, z=130.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=0.0, y=260.0, z=-120.0)),
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
        topo_name = JointTopology.get_name(joint.topology).split("_")[-1]
        viewer.scene.add(Tag(text=topo_name, position=joint.location, height=40, color=Color.blue()))

    # draw centerline
    for beam in model.beams:
        viewer.scene.add(beam.centerline)
        viewer.scene.add(beam.geometry)
        viewer.scene.add(Tag(text=str(beam.graph_node), position=beam.centerline.midpoint, height=40, color=Color.black()))

    tol = Tolerance(absolute=0.01)
    num_of_beams = len(list(model.beams))

    ### find triplets only
    # analyzer = TripletAnalyzer(model, tolerance=Tolerance(absolute=0.01))

    ### find quads only
    # analyzer = QuadAnalyzer(model, tolerance=Tolerance(absolute=0.01))

    ### find all clusters up to n beams, then n-1 beams, then n-2 beams, etc.
    analyzer = MaxNCompositeAnalyzer(model, n=num_of_beams, tolerance=tol)

    clusters = analyzer.find()

    size_to_color = create_color_map(list(sorted({len(cluster) for cluster in clusters})))
    for cluster in clusters:
        size = len(cluster)
        color = size_to_color[size]
        viewer.scene.add(cluster.location, pointsize=50, color=color)

    viewer.show()


if __name__ == "__main__":
    main()
