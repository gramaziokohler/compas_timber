import Rhino.Geometry as rg
from utils.rhino_compas import cBox2rBox
from utils.rhino_compas import cFrame2rPln


def trim_beam_with_plane(beam, cutting_plane):
    cpln = cFrame2rPln(cutting_plane)
    brep = cBox2rBox(beam.shape)
    rg.Brep.Trim(cpln)
    pass
