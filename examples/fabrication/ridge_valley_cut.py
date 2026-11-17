"""RidgeValleyCut: two inclined planes which meet in a ridge along the element."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import RidgeValleyCut

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(
    RidgeValleyCut(start_x=100.0, start_y=60.0, inclination_ref_side=30.0, inclination_opp_side=30.0, start_limited=True, end_limited=True, length=600.0, ref_side_index=2)
)

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
