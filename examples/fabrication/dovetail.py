"""Dovetail: the corner lock of a log, with a sloped tail."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Dovetail

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(
    Dovetail(
        orientation="end", cut_off=True, start_x=700.0, start_y=30.0, start_depth=50.0, slope=10.0, length=150.0, height_ref_side=60.0, height_opp_side=30.0, ref_side_index=2
    )
)

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
