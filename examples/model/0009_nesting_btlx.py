import argparse
import os

from compas.data import json_load
from compas.geometry import Vector
from compas.tolerance import TOL
from compas_viewer.viewer import Viewer

from compas_timber.connections import JointTopology
from compas_timber.connections import LButtJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxWriter
from compas_timber.model import TimberModel
from compas_timber.planning import BeamNester
from compas_timber.planning import BeamStock

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(HERE), "..", "data")
LINES = os.path.join(HERE, "stand.json")
BLADE_THICKNESS = 3.2

TOL.absolute = 1e-3


def create_viewer():
    # draw inflated centerlines
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


def create_stand_model():
    """Create and return a timber stand model with joints."""
    # Load centerlines from file
    lines = json_load(LINES)

    model = TimberModel()

    # Add beams to model
    CROSS_SQUARE = (100, 100)
    CROSS_TALL = (100, 60)
    NORMAL_VERTICALS = Vector(0, 1, 0)

    # Create the beams with the right cross section depending on their category
    # Assign normal to the beams whose centerlines are aligned with the zaxis
    for category, lines in lines.items():
        for line in lines:
            if category in ["main", "support", "window"]:
                height, width = CROSS_SQUARE
            else:
                height, width = CROSS_TALL
            normal = NORMAL_VERTICALS if category == "verticals" else None
            beam = Beam.from_centerline(centerline=line, height=height, width=width, z_vector=normal)
            beam.attributes["category"] = category
            beam.name = category
            model.add_element(beam)

    # analyze connections and create joint candidates
    model.connect_adjacent_beams()

    # create joints for L and T connections
    for candidate in model.joint_candidates:
        beam_a, beam_b = candidate.elements
        if candidate.topology == JointTopology.TOPO_L:
            LButtJoint.create(model, beam_a, beam_b)
        elif candidate.topology == JointTopology.TOPO_T:
            TButtJoint.create(model, beam_a, beam_b, mill_depth=5.0)

    model.process_joinery()
    return model


def generate_nesting(model):
    """Generate nesting for the given timber model."""
    stock_catalog = [BeamStock(5000, (100, 100)), BeamStock(5000, (100, 60))]
    nester = BeamNester(model, stock_catalog, spacing=BLADE_THICKNESS)
    return nester.nest(fast=False)


def visualize_model(model):
    """Visualize the model using the COMPAS viewer."""
    # setup the viewer
    viewer = create_viewer()

    # draw centerline
    for beam in model.beams:
        viewer.scene.add(beam.centerline)

    # draw geometry (with features)
    for beam in model.beams:
        viewer.scene.add(beam.geometry)

    viewer.show()


def serialize_nesting(nesting_result, output_path=None):
    """Serialize the nesting result to JSON."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "nesting_test.json")

    nesting_result.to_json(output_path, pretty=True)
    print(f"Nesting result written to {output_path}")


def export_btlx(model, output_path=None, nesting_result=None):
    """Export the model to BTLx format."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "nesting_test.btlx")
    writer = BTLxWriter()
    writer.write(model, output_path, nesting_result=nesting_result)
    print(f"BTLx exported to {output_path}")


def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(description="Generate a timber stand model with joints")
    parser.add_argument("--visualize", "-v", action="store_true", help="Visualize the model in the COMPAS viewer")
    parser.add_argument("--serialize", "-s", metavar="PATH", nargs="?", const="default", help="Serialize the model to JSON (optionally specify output path)")
    parser.add_argument("--export-btlx", "-b", metavar="PATH", nargs="?", const="default", help="Export the model to BTLx format (optionally specify output path)")

    args = parser.parse_args()

    # Create the model
    print("Creating timber stand model...")
    model = create_stand_model()
    print(f"Model created with {len(list(model.elements()))} elements and {len(model.joints)} joints")

    print("Generating nesting...")
    nesting_result = generate_nesting(model)
    print(f"Nesting generated with {len(nesting_result.stocks)} stocks")

    if args.serialize:
        print("Serializing nesting result...")
        output_path = None if args.serialize == "default" else args.serialize
        serialize_nesting(nesting_result, output_path)

    if args.export_btlx:
        print("Exporting to BTLx...")
        output_path = None if args.export_btlx == "default" else args.export_btlx
        export_btlx(model, output_path, nesting_result=nesting_result)

        # Execute requested actions
    if args.visualize:
        print("Visualizing model...")
        visualize_model(model)

    # If no arguments provided, show help
    if not any([args.visualize, args.serialize, args.export_btlx]):
        parser.print_help()


if __name__ == "__main__":
    main()
