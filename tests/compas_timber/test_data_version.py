from unittest.mock import patch
import warnings

from compas.data import json_dumps
from compas.data import json_loads

from compas_timber.model import TimberModel


def test_serialization_version_matches():
    """Roundtrip serialization with matching version should not warn."""
    model = TimberModel()
    data = json_dumps(model)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        restored = json_loads(data)
        version_warnings = [x for x in w if "compas_timber version" in str(x.message)]
        assert len(version_warnings) == 0

    assert isinstance(restored, TimberModel)


def test_serialization_version_mismatch():
    """Roundtrip with a different version should emit a warning."""
    model = TimberModel()
    data = json_dumps(model)

    with patch("compas_timber.data.compas_timber") as mock_ct:
        mock_ct.__version__ = "0.0.0-fake"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            json_loads(data)
            version_warnings = [x for x in w if "compas_timber version" in str(x.message)]
            assert len(version_warnings) == 1


def test_serialization_no_version_key():
    """Data without __version__ key should deserialize without warning."""
    model = TimberModel()
    data_str = json_dumps(model)
    # Parse, remove the version key, and re-serialize
    import json

    raw = json.loads(data_str)

    def _strip_version(obj):
        if isinstance(obj, dict):
            obj.pop("__version__", None)
            for v in obj.values():
                _strip_version(v)
        elif isinstance(obj, list):
            for v in obj:
                _strip_version(v)

    _strip_version(raw)
    data_str = json.dumps(raw)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        restored = json_loads(data_str)
        version_warnings = [x for x in w if "compas_timber version" in str(x.message)]
        assert len(version_warnings) == 0

    assert isinstance(restored, TimberModel)


def test_data_contains_version():
    """The __data__ property should include a __version__ key."""
    model = TimberModel()
    data = model.__data__
    assert "__version__" in data
