from compas_timber.fasteners import Fastener


def test_abstract_fastener():
    try:
        fastener = Fastener()
    except Exception as e:
        assert str(e)
