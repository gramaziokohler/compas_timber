from compas.geometry import Frame, Point, Vector
from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.parts.beam import Beam
from compas_timber.connections.joint import Joint
import copy
import compas
import pickle

def test_json():
    A = TimberAssembly()
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, width = 0.1, height = 0.2, length = 1.0)
    B2 = Beam(F1, width = 0.2, height = 0.4, length = 1.0)

    A.add_beam(B1)
    A.add_beam(B2)
    J = Joint(A,[B1, B2])

    filepath = r"C:\Users\aapolina\CODE\compas_timber\data\assembly.json"
    #compas.json_dump(A.data, filepath)
    with open(filepath,'wb') as f: pickle.dump(A,f)



if __name__ == "__main__":
    test_json()
    print("\n *** all tests passed ***\n\n")

    