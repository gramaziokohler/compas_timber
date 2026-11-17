from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_pb.generated import message_pb2 as _message_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StructuralSegmentData(_message.Message):
    __slots__ = ("guid", "name", "line", "frame", "cross_section", "cross_section_set", "attributes")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    CROSS_SECTION_FIELD_NUMBER: _ClassVar[int]
    CROSS_SECTION_SET_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    line: _geometry_pb2.LineData
    frame: _geometry_pb2.FrameData
    cross_section: _containers.RepeatedScalarFieldContainer[float]
    cross_section_set: bool
    attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., line: _Optional[_Union[_geometry_pb2.LineData, _Mapping]] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., cross_section: _Optional[_Iterable[float]] = ..., cross_section_set: bool = ..., attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ...) -> None: ...
