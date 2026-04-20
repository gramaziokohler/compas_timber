import os

from compas.data import json_load
from compas_viewer.viewer import Viewer

from compas_timber.model import TimberModel
from compas_timber.structural import StructuralGraph


def main():

    HERE = os.path.dirname(__file__)
    PATH = os.path.join(HERE, "reciprocal_2_dev0.json")

    model = json_load(PATH)

    assert isinstance(model, TimberModel)

    model.create_beam_structural_segments()

    graph = StructuralGraph.from_model(model)

    viewer = Viewer()
    viewer.renderer.camera.far = 1_000_000.0
    viewer.renderer.camera.position = [10_000.0, 10_000.0, 10_000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"

    for node in graph.nodes():
        viewer.scene.add(graph.node_point(node), pointsize=5, show_points=True)

    for u, v in graph.beam_edges:
        viewer.scene.add(graph.segment(u, v).line, linewidth=1, linecolor=(0, 0, 255))

    for u, v in graph.connector_edges:
        viewer.scene.add(graph.segment(u, v).line, linewidth=3, linecolor=(255, 0, 0))

    viewer.show()


if __name__ == "__main__":
    main()
