"""ProfileCambered: a curved profile along the element."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import ProfileCambered

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(ProfileCambered(start_x=100.0, length=600.0, start_depth=40.0, max_depth=60.0, min_depth=10.0, end_depth=40.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
