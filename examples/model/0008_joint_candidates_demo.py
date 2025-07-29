"""
Joint Candidates Demo

This example demonstrates the new joint candidate system in compas_timber.
It shows how to:
1. Create joint candidates using connect_adjacent_beams()
2. Iterate through candidates and promote them to actual joints based on topology rules
3. Visualize the results using the viewer

The script creates a simple timber structure with various beam intersections
and demonstrates the two-stage process: candidate detection and joint creation.
"""

from compas.geometry import Line
from compas.geometry import Point
from compas_viewer.viewer import Viewer

from compas_timber.connections import BallNodeJoint
from compas_timber.connections import JointTopology
from compas_timber.connections import LMiterJoint
from compas_timber.connections import NBeamKDTreeAnalyzer
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


def create_viewer():
    """Create and configure the viewer."""
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [5000.0, 5000.0, 5000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


def create_demo_structure():
    """Create a demo timber structure with various beam intersections."""
    model = TimberModel()

    HEIGHT = 1200
    WIDTH = 600

    centerlines = [
        Line(Point(x=0.0, y=18000.0, z=10000.0), Point(x=35000.0, y=18000.0, z=0.0)),
        Line(Point(x=0.0, y=0.0, z=10000.0), Point(x=0.0, y=18000.0, z=10000.0)),
        Line(Point(x=35000.0, y=0.0, z=0.0), Point(x=0.0, y=0.0, z=10000.0)),
        Line(Point(x=35000.0, y=0.0, z=0.0), Point(x=0.0, y=0.0, z=0.0)),
        Line(Point(x=35000.0, y=18000.0, z=0.0), Point(x=35000.0, y=0.0, z=0.0)),
        Line(Point(x=0.0, y=18000.0, z=0.0), Point(x=35000.0, y=18000.0, z=0.0)),
        Line(Point(x=0.0, y=0.0, z=0.0), Point(x=0.0, y=18000.0, z=0.0)),
        Line(Point(x=0.0, y=11548.433874301914, z=10000.0), Point(x=0.0, y=6783.40750593623, z=0.0)),
        Line(Point(x=0.0, y=0.0, z=0.0), Point(x=0.0, y=0.0, z=10000.0)),
        Line(Point(x=0.0, y=18000.0, z=0.0), Point(x=0.0, y=18000.0, z=10000.0)),
        Line(Point(x=0.0, y=0.0, z=10000.0), Point(x=17000.0, y=10000.0, z=0.0)),
        Line(Point(x=0.0, y=18000.0, z=10000.0), Point(x=17000.0, y=10000.0, z=0.0)),
        Line(Point(x=17000.0, y=10000.0, z=0.0), Point(x=35000.0, y=0.0, z=0.0)),
        Line(Point(x=35000.0, y=18000.0, z=0.0), Point(x=17000.0, y=10000.0, z=0.0)),
        Line(Point(x=17211.29780042542, y=18000.0, z=0.0), Point(x=17000.0, y=10000.0, z=0.0)),
        Line(Point(x=19638.64663884219, y=0.0, z=0.0), Point(x=17000.0, y=10000.0, z=0.0)),
    ]

    beams = []
    for i, centerline in enumerate(centerlines):
        beam = Beam.from_centerline(centerline, height=HEIGHT, width=WIDTH)
        beam.name = f"beam_{i + 1}"
        beams.append(beam)
        model.add_element(beam)

    return model


def find_and_create_ball_node_joints(model):
    """Find clusters of 6 beams and create BallNodeJoints for them."""
    analyzer = NBeamKDTreeAnalyzer(model, n=6)
    clusters = analyzer.find()

    ball_node_count = 0
    for cluster in clusters:
        try:
            BallNodeJoint.create(model, *cluster.elements, ball_diameter=1000.0)
            ball_node_count += 1
        except Exception:
            pass


def promote_candidates_to_joints(model):
    """Promote joint candidates to actual joints based on topology rules."""
    ball_node_beams = set()
    for joint in model.joints:
        if isinstance(joint, BallNodeJoint):
            ball_node_beams.update(joint.elements)

    l_joints = 0
    t_joints = 0

    for candidate in model.joint_candidates:
        beam_a, beam_b = candidate.elements

        if beam_a in ball_node_beams or beam_b in ball_node_beams:
            continue

        if candidate.topology == JointTopology.TOPO_L:
            LMiterJoint.create(model, beam_a, beam_b)
            l_joints += 1
        elif candidate.topology == JointTopology.TOPO_T:
            TButtJoint.create(model, beam_a, beam_b)
            t_joints += 1

    return l_joints, t_joints


def visualize_structure(model, viewer):
    """Visualize the timber structure in the viewer."""

    # Add centerlines for all beams
    for beam in model.beams:
        viewer.scene.add(beam.centerline, linecolor=(0, 0, 255), linewidth=2)

    # Add beam geometry (with features)
    for beam in model.beams:
        viewer.scene.add(beam.geometry, facecolor=(0.8, 0.6, 0.4), linecolor=(0.4, 0.3, 0.2))

    # this doesn't work cause OCC brep can't yet cap ends.
    # Add generated elements (like BallNodeFasteners)
    # for element in model.elements():
    #     if element.is_fastener:
    #         viewer.scene.add(element.geometry, facecolor=(1, 0, 0), linecolor=(0.5, 0, 0))

    # Add joint locations as points
    for joint in model.joints:
        viewer.scene.add(joint.location, pointcolor=(255, 0, 0), pointsize=10)

    # Add candidate locations as smaller points (if any remain)
    for candidate in model.joint_candidates:
        viewer.scene.add(candidate.location, pointcolor=(255, 255, 0), pointsize=5)


def main():
    """Main demonstration function."""
    model = create_demo_structure()
    model.connect_adjacent_beams()

    find_and_create_ball_node_joints(model)
    l_joints, t_joints = promote_candidates_to_joints(model)

    errors = model.process_joinery()

    ball_node_joints = len([j for j in model.joints if isinstance(j, BallNodeJoint)])

    print(f"Created {len(model.joints)} joints:")
    print(f"  - {ball_node_joints} BallNodeJoints (6-beam clusters)")
    print(f"  - {l_joints} LMiterJoints (L topology)")
    print(f"  - {t_joints} TButtJoints (T topology)")

    if errors:
        print(f"Warning: {len(errors)} errors during joinery processing")

    viewer = create_viewer()
    visualize_structure(model, viewer)
    viewer.show()


if __name__ == "__main__":
    main()
