from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GuidRef(_message.Message):
    __slots__ = ("index", "raw", "text")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    RAW_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    index: int
    raw: bytes
    text: str
    def __init__(self, index: _Optional[int] = ..., raw: _Optional[bytes] = ..., text: _Optional[str] = ...) -> None: ...

class PointList(_message.Message):
    __slots__ = ("coordinates",)
    COORDINATES_FIELD_NUMBER: _ClassVar[int]
    coordinates: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, coordinates: _Optional[_Iterable[float]] = ...) -> None: ...

class ModelFeatureBaseData(_message.Message):
    __slots__ = ("guid", "name")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guid: GuidRef
    name: str
    def __init__(self, guid: _Optional[_Union[GuidRef, _Mapping]] = ..., name: _Optional[str] = ...) -> None: ...

class BeamFeatureData(_message.Message):
    __slots__ = ("guid", "name")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guid: GuidRef
    name: str
    def __init__(self, guid: _Optional[_Union[GuidRef, _Mapping]] = ..., name: _Optional[str] = ...) -> None: ...

class PlateFeatureData(_message.Message):
    __slots__ = ("guid", "name")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guid: GuidRef
    name: str
    def __init__(self, guid: _Optional[_Union[GuidRef, _Mapping]] = ..., name: _Optional[str] = ...) -> None: ...

class ColumnFeatureData(_message.Message):
    __slots__ = ("guid", "name")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guid: GuidRef
    name: str
    def __init__(self, guid: _Optional[_Union[GuidRef, _Mapping]] = ..., name: _Optional[str] = ...) -> None: ...

class ModelFeatureData(_message.Message):
    __slots__ = ("base_feature", "beam_feature", "plate_feature", "column_feature")
    BASE_FEATURE_FIELD_NUMBER: _ClassVar[int]
    BEAM_FEATURE_FIELD_NUMBER: _ClassVar[int]
    PLATE_FEATURE_FIELD_NUMBER: _ClassVar[int]
    COLUMN_FEATURE_FIELD_NUMBER: _ClassVar[int]
    base_feature: ModelFeatureBaseData
    beam_feature: BeamFeatureData
    plate_feature: PlateFeatureData
    column_feature: ColumnFeatureData
    def __init__(self, base_feature: _Optional[_Union[ModelFeatureBaseData, _Mapping]] = ..., beam_feature: _Optional[_Union[BeamFeatureData, _Mapping]] = ..., plate_feature: _Optional[_Union[PlateFeatureData, _Mapping]] = ..., column_feature: _Optional[_Union[ColumnFeatureData, _Mapping]] = ...) -> None: ...
