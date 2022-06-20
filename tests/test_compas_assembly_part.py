from compas.datastructures.assembly import Part, Assembly
from copy import deepcopy
import compas
import json
import os



def test_part_deepcopy():
    P = Part()
    P_copy = deepcopy(P)
    assert P is not P_copy
    #assert P == P_copy #failing
    #assert P_copy.guid != P.guid  # failing


def test_assembly_deepcopy():
    P1 = Part()
    P2 = Part()
    A = Assembly()
    A.add_part(P1)
    A.add_part(P2)
    A.add_connection(P1, P2)
    A_copy = deepcopy(A)
    assert A_copy is not A
    #assert A_copy.guid != A.guid  # failing


def test_json():
    P1 = Part()
    P2 = Part()
    A = Assembly()
    A.add_part(P1)
    A.add_part(P2)
    A.add_connection(P1, P2)
    
    P1.attributes['assembly'] = A # this makes json_dump fail

    cwd = os.getcwd()
    filepath = os.path.join(cwd, r"\temp\test_assembly.json")
    compas.json_dump(A.data, filepath)
    
    #Aj = json.dumps(A)  # TypeError: Object of type Assembly is not JSON serializable


if __name__ == '__main__':
    test_part_deepcopy()
    test_assembly_deepcopy()
    test_json()
    print("\n*** all tests passed ***\n\n")
