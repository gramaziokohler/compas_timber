from compas_timber.fasteners import Fastener


def test_fastener_initialization():
    fastener = Fastener()
    assert fastener.attributes == {}
    assert fastener.debug_info == []


def test_fastener_repr():
    fastener = Fastener()
    assert repr(fastener) == "Fastener(frame=Frame(point=Point(x=0.0, y=0.0, z=0.0), xaxis=Vector(x=1.0, y=0.0, z=0.0), yaxis=Vector(x=0.0, y=1.0, z=0.0)), name=Fastener)"


def test_fastener_str():
    fastener = Fastener()
    assert str(fastener) == "<Fastener Fastener>"


def test_fastener_is_fastener():
    fastener = Fastener()
    assert fastener.is_fastener is True
