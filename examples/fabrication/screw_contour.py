"""ScrewContour: screws along a path, which leave the volume as it is. The path is drawn for this image."""

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import ScrewContour
from compas_timber.fabrication import SimpleContour

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
path = Polyline([[150.0, 30.0, 0.0], [650.0, 30.0, 0.0], [650.0, 90.0, 0.0]])
beam.add_feature(ScrewContour(contour=SimpleContour(path, screw_length=80.0, screw_diameter=6.0, nail_spacing=150.0), ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
side = Transformation.from_frame(beam.ref_sides[2])
viewer.scene.add(path.transformed(side), linecolor=Color.red(), linewidth=3)
viewer.show()
