"""TyroleanDovetail: the Tyrolean corner lock of a log, here with a Frosch."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Frosch
from compas_timber.fabrication import TyroleanDovetail

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(
    TyroleanDovetail(
        orientation="end",
        cut_off=True,
        start_x=700.0,
        start_y=30.0,
        start_depth=50.0,
        angle=90.0,
        slope=10.0,
        length=150.0,
        height=60.0,
        frosch=Frosch(20.0, 10.0),
        ref_side_index=2,
    )
)

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
