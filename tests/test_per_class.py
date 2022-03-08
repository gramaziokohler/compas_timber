#one or more test per method in a class, in isolation 
#a separate test file for each class

import pytest


def test_beam_fails_smth():
    with pytest.raises(ValueError):
        B = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), "0.100", 0.200)
        

def test_beam_constructor():
    B = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), Vector(0, 0, 1), 0.100, 0.200)
    #test if length is =1
    assert B.length == 1.0 #use allclose from numppy

   