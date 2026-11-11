"""ScarfJoint: a lengthwise joint with a sloped lap and optional drill holes."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import ScarfJoint

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(
    ScarfJoint(orientation="end", start_x=500.0, inclination=20.0, lap_length=60.0, lap_depth=40.0, length=240.0, depth_opp_side=40.0, num_drill_hole=2, ref_side_index=2)
)

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
