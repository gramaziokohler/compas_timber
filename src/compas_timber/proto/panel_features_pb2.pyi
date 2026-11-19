from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class OpeningData(_message.Message):
    __slots__ = ("guid", "name", "frame", "features", "material", "outline_a", "outline_b", "opening_type")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    MATERIAL_FIELD_NUMBER: _ClassVar[int]
    OUTLINE_A_FIELD_NUMBER: _ClassVar[int]
    OUTLINE_B_FIELD_NUMBER: _ClassVar[int]
    OPENING_TYPE_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    frame: _geometry_pb2.FrameData
    features: _containers.RepeatedCompositeFieldContainer[_common_pb2.ModelFeatureData]
    material: _common_pb2.GuidRef
    outline_a: _geometry_pb2.PolylineData
    outline_b: _geometry_pb2.PolylineData
    opening_type: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., features: _Optional[_Iterable[_Union[_common_pb2.ModelFeatureData, _Mapping]]] = ..., material: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., outline_a: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., outline_b: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., opening_type: _Optional[str] = ...) -> None: ...

class PanelConnectionInterfaceData(_message.Message):
    __slots__ = ("guid", "name", "frame", "features", "material", "polyline", "edge_index", "interface_role")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    MATERIAL_FIELD_NUMBER: _ClassVar[int]
    POLYLINE_FIELD_NUMBER: _ClassVar[int]
    EDGE_INDEX_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_ROLE_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    frame: _geometry_pb2.FrameData
    features: _containers.RepeatedCompositeFieldContainer[_common_pb2.ModelFeatureData]
    material: _common_pb2.GuidRef
    polyline: _geometry_pb2.PolylineData
    edge_index: int
    interface_role: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., features: _Optional[_Iterable[_Union[_common_pb2.ModelFeatureData, _Mapping]]] = ..., material: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., polyline: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., edge_index: _Optional[int] = ..., interface_role: _Optional[str] = ...) -> None: ...

class PanelFeatureData(_message.Message):
    __slots__ = ("opening", "connection_interface")
    OPENING_FIELD_NUMBER: _ClassVar[int]
    CONNECTION_INTERFACE_FIELD_NUMBER: _ClassVar[int]
    opening: OpeningData
    connection_interface: PanelConnectionInterfaceData
    def __init__(self, opening: _Optional[_Union[OpeningData, _Mapping]] = ..., connection_interface: _Optional[_Union[PanelConnectionInterfaceData, _Mapping]] = ...) -> None: ...
