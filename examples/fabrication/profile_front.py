"""ProfileFront: a profile of two arcs at the end of the element."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import ProfileFront

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(ProfileFront(orientation="end", start_x=700.0, depth=20.0, radius1=100.0, radius2=100.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
