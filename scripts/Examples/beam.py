import Rhino.Geometry as rg

from compas_timber.parts.beam import Beam
from compas_timber.utils.rhino_compas import cBox2rBox
from compas_timber.utils.rhino_compas import rPln2cFrame

L = 10
W = 0.1
H = 0.2

beam = Beam(rPln2cFrame(rg.Plane.WorldXY), L, W, H)

beam = Beam.from_frame(rPln2cFrame(rg.Plane.WorldXY), W, H, L)

geometry = None

shape = cBox2rBox(beam.shape)
