"""LogHouseJoint: laps on the four sides of a log, where it crosses another one."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import LogHouseJoint

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(
    LogHouseJoint(
        start_x=400.0,
        length_ref_side=120.0,
        depth_ref_side=30.0,
        length_opp_side=120.0,
        depth_opp_side=30.0,
        length_ref_edge=120.0,
        depth_ref_edge=20.0,
        length_opp_edge=120.0,
        depth_opp_edge=20.0,
        ref_side_index=2,
    )
)

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
