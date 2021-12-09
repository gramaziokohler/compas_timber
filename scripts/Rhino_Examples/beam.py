import Rhino.Geometry as rg
from compas_timber.elements.beam2 import Beam
from compas_timber.utils.rhino_compas import rPln2cFrame

L = 10
W = 0.1
H = 0.2


b1 = Beam(rPln2cFrame(rg.Plane.WorldXY),L,W,H)

b1 = Beam.from_frame(rPln2cFrame(rg.Plane.WorldXY),W,H,L)
print b1


