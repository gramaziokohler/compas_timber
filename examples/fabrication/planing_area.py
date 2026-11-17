"""PlaningArea: planes an area, here around an aperture."""

from compas.geometry import Frame
from compas.geometry import Polyline
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Apertures
from compas_timber.fabrication import PlaningArea
from compas_timber.fabrication import SimpleContour

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
outline = Polyline([[200.0, 20.0, 0.0], [500.0, 20.0, 0.0], [500.0, 100.0, 0.0], [200.0, 100.0, 0.0], [200.0, 20.0, 0.0]])
hole = Polyline([[300.0, 40.0, 0.0], [400.0, 40.0, 0.0], [400.0, 80.0, 0.0], [300.0, 80.0, 0.0], [300.0, 40.0, 0.0]])
beam.add_feature(PlaningArea(contour=SimpleContour(outline), apertures=Apertures([SimpleContour(hole)]), depth=15.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
