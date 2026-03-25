"""Structural segments example.

This script demonstrates how to extract a structural model from a TimberModel.

The workflow is:
1. Build a TimberModel from beam centerlines.
2. Auto-detect joint candidates with ``connect_adjacent_beams``.
3. Call ``create_beam_structural_segments`` to split each beam centerline at
   every joint location and create virtual connector elements between beams
   whose centerlines do not intersect.
4. Retrieve the resulting segments and connectors and visualise them.

Each beam is split into one or more ``StructuralSegment`` objects that together
span the full centerline.  Adjacent beams that do not share an intersection point
get a short "virtual" connector segment bridging the gap between their centerlines.

Run this script from the repository root::

    python examples/model/0010_structural_segments.py

"""

import os

from compas.colors import Color
from compas.data import json_load
from compas.geometry import Point
from compas_viewer.scene import Tag
from compas_viewer.viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.model import TimberModel


HERE = os.path.dirname(__file__)
LINES = os.path.join(HERE, "lines.json")

# ----- colours used in the viewer -----
COLOR_BEAM = Color.grey()
COLOR_SEGMENT = Color.from_hex("#2B7CB8")  # blue  – beam structural segments
COLOR_CONNECTOR = Color.from_hex("#E05C1A")  # orange – virtual connector segments
COLOR_CANDIDATE = Color.from_hex("#1DB847")  # green  – joint candidate locations


def main():
    # ------------------------------------------------------------------
    # 1. Load centerlines and build the timber model
    # ------------------------------------------------------------------
    lines = json_load(LINES)

    model = TimberModel()
    for line in lines:
        beam = Beam.from_centerline(centerline=line, width=60, height=120)
        model.add_element(beam)

    # ------------------------------------------------------------------
    # 2. Auto-detect adjacent beam pairs and store them as JointCandidates
    #    max_distance controls the tolerance used when searching for
    #    beam-end / beam-mid topology.
    # ------------------------------------------------------------------
    model.connect_adjacent_beams(max_distance=14)

    print("Beams            :", len(model.beams))
    print("Joint candidates :", len(list(model.joint_candidates)))

    # ------------------------------------------------------------------
    # 3. Create structural segments
    #    - Each beam is split at every joint-candidate location.
    #    - For non-intersecting beam pairs a short virtual connector
    #      segment is created between the closest points on their axes.
    # ------------------------------------------------------------------
    model.create_beam_structural_segments()

    # ------------------------------------------------------------------
    # 4. Collect all structural segments from the model
    # ------------------------------------------------------------------
    beam_segments = []
    for beam in model.beams:
        # get_beam_structural_segments returns the ordered list of
        # StructuralSegment objects that span this beam's centerline.
        segs = model.get_beam_structural_segments(beam)
        beam_segments.extend(segs)
        print(f"  beam {beam.graphnode:>2d}  →  {len(segs)} segment(s), lengths: {[round(s.line.length, 1) for s in segs]}")

    connector_segments = []
    for candidate in model.joint_candidates:
        # For each candidate, check whether the solver produced a virtual
        # connector between the two beams.  Non-intersecting pairs (e.g.
        # parallel or slightly offset beams) will have one connector; truly
        # intersecting pairs will have none.
        beam_a, beam_b = candidate.interactions[0]
        segs = model.get_structural_connector_segments(beam_a, beam_b)
        connector_segments.extend(segs)
        if segs:
            print(f"  connector {beam_a.graphnode} ↔ {beam_b.graphnode}  →  {len(segs)} segment(s)")

    print(f"\nTotal beam segments     : {len(beam_segments)}")
    print(f"Total connector segments: {len(connector_segments)}")

    # ------------------------------------------------------------------
    # 5. Visualise
    # ------------------------------------------------------------------
    viewer = Viewer()
    viewer.renderer.camera.far = 1_000_000.0
    viewer.renderer.camera.position = [10_000.0, 10_000.0, 10_000.0]
    viewer.renderer.camera.pandelta = 5.0
    viewer.renderer.rendermode = "ghosted"

    # Ghost beam geometry for context
    for beam in model.beams:
        viewer.scene.add(beam.geometry, color=COLOR_BEAM, opacity=0.15)

    # Beam structural segments (solid coloured lines)
    for i, seg in enumerate(beam_segments):
        viewer.scene.add(seg.line, color=COLOR_SEGMENT, linewidth=3)
        viewer.scene.add(
            Tag(
                text=f"s{i}",
                position=seg.line.midpoint,
                height=20,
                color=COLOR_SEGMENT,
            )
        )

    # Virtual connector segments between non-intersecting beam pairs
    for seg in connector_segments:
        viewer.scene.add(seg.line, color=COLOR_CONNECTOR, linewidth=4)

    # Joint candidate locations (nodes in the structural model)
    for candidate in model.joint_candidates:
        viewer.scene.add(
            Tag(
                text="J",
                position=Point(*candidate.location),
                height=25,
                color=COLOR_CANDIDATE,
            )
        )

    viewer.show()


if __name__ == "__main__":
    main()
