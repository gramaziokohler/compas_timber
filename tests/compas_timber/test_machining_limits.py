from compas_timber.fabrication import MachiningLimits


def test_machining_limits():
    ml = MachiningLimits()
    assert ml.face_limited_start
    assert ml.face_limited_end
    assert ml.face_limited_front
    assert ml.face_limited_back
    assert ml.face_limited_top
    assert ml.face_limited_bottom


def test_machining_limits_from_dict():
    mldict = {
        "FaceLimitedStart": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
        "FaceLimitedBack": True,
        "FaceLimitedTop": False,
        "FaceLimitedBottom": True,
    }

    ml = MachiningLimits.from_dict(mldict)
    assert not ml.face_limited_start
    assert ml.face_limited_end
    assert not ml.face_limited_front
    assert ml.face_limited_back
    assert not ml.face_limited_top
    assert ml.face_limited_bottom

    mldict = {
        "FaceLimitedStart": True,
        "FaceLimitedEnd": False,
        "FaceLimitedFront": True,
        "FaceLimitedBack": False,
        "FaceLimitedTop": True,
        "FaceLimitedBottom": False,
    }

    ml = MachiningLimits.from_dict(mldict)
    assert ml.face_limited_start
    assert not ml.face_limited_end
    assert ml.face_limited_front
    assert not ml.face_limited_back
    assert ml.face_limited_top
    assert not ml.face_limited_bottom

    assert ml.as_dict() == mldict


def test_from_dict_errors():
    mldict = {
        "FaceLimited_Start": False,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
        "FaceLimitedBack": True,
        "FaceLimitedTop": False,
        "FaceLimitedBottom": True,
    }
    try:
        MachiningLimits.from_dict(mldict)
    except Exception as e:
        assert isinstance(e, ValueError), f"The key must be one of the following: {[limit for limit in MachiningLimits.EXPECTED_KEYS]}"

    mldict = {
        "FaceLimitedStart": 42,
        "FaceLimitedEnd": True,
        "FaceLimitedFront": False,
        "FaceLimitedBack": True,
        "FaceLimitedTop": False,
        "FaceLimitedBottom": True,
    }
    try:
        MachiningLimits.from_dict(mldict)
    except Exception as e:
        assert isinstance(e, ValueError), "The values must be a boolean."
