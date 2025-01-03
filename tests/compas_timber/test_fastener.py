from compas_timber.elements import Fastener


def test_fastener_initialization():
    fastener = Fastener()
    assert fastener.attributes == {}
    assert fastener.debug_info == []


def test_fastener_repr():
    fastener = Fastener()
    assert repr(fastener) == "Fastener(frame=None, name=Fastener)"


def test_fastener_str():
    fastener = Fastener()
    assert str(fastener) == "<Fastener Fastener>"


def test_fastener_is_fastener():
    fastener = Fastener()
    assert fastener.is_fastener is True
