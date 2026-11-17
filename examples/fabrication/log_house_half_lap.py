"""LogHouseHalfLap: the end of a log, reduced in height from both sides."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import LogHouseHalfLap

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(LogHouseHalfLap(orientation="end", start_x=650.0, length=120.0, depth_ref_side=50.0, depth_opp_side=50.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
