"""ProfileHead: stairs and arcs at the head of the element."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import ProfileArc
from compas_timber.fabrication import ProfileHead

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(ProfileHead(orientation="end", start_x=750.0, arc1=ProfileArc(radius=60.0), ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
