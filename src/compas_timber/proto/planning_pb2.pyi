from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_pb.generated import message_pb2 as _message_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Model3dData(_message.Message):
    __slots__ = ("guid", "name", "id", "location", "geometry", "element_id", "obj_filepath")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_ID_FIELD_NUMBER: _ClassVar[int]
    OBJ_FILEPATH_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    id: str
    location: _geometry_pb2.FrameData
    geometry: _message_pb2.AnyData
    element_id: str
    obj_filepath: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., id: _Optional[str] = ..., location: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., geometry: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ..., element_id: _Optional[str] = ..., obj_filepath: _Optional[str] = ...) -> None: ...

class Text3dData(_message.Message):
    __slots__ = ("guid", "name", "id", "location", "text", "size")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    id: str
    location: _geometry_pb2.FrameData
    text: str
    size: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., id: _Optional[str] = ..., location: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., text: _Optional[str] = ..., size: _Optional[float] = ...) -> None: ...

class LinearDimensionData(_message.Message):
    __slots__ = ("guid", "name", "id", "location", "start", "end", "char_size", "offset")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    CHAR_SIZE_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    id: str
    location: _geometry_pb2.FrameData
    start: _geometry_pb2.PointData
    end: _geometry_pb2.PointData
    char_size: float
    offset: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., id: _Optional[str] = ..., location: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., start: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., end: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., char_size: _Optional[float] = ..., offset: _Optional[float] = ...) -> None: ...

class InstructionData(_message.Message):
    __slots__ = ("model_3d", "text_3d", "linear_dimension")
    MODEL_3D_FIELD_NUMBER: _ClassVar[int]
    TEXT_3D_FIELD_NUMBER: _ClassVar[int]
    LINEAR_DIMENSION_FIELD_NUMBER: _ClassVar[int]
    model_3d: Model3dData
    text_3d: Text3dData
    linear_dimension: LinearDimensionData
    def __init__(self, model_3d: _Optional[_Union[Model3dData, _Mapping]] = ..., text_3d: _Optional[_Union[Text3dData, _Mapping]] = ..., linear_dimension: _Optional[_Union[LinearDimensionData, _Mapping]] = ...) -> None: ...

class StepData(_message.Message):
    __slots__ = ("guid", "name", "element_ids", "actor", "location", "geometry", "instructions", "is_built", "is_planned", "elements_held", "priority")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_IDS_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    IS_BUILT_FIELD_NUMBER: _ClassVar[int]
    IS_PLANNED_FIELD_NUMBER: _ClassVar[int]
    ELEMENTS_HELD_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    element_ids: _containers.RepeatedScalarFieldContainer[str]
    actor: str
    location: _geometry_pb2.FrameData
    geometry: str
    instructions: _containers.RepeatedCompositeFieldContainer[InstructionData]
    is_built: bool
    is_planned: bool
    elements_held: _containers.RepeatedScalarFieldContainer[str]
    priority: int
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., element_ids: _Optional[_Iterable[str]] = ..., actor: _Optional[str] = ..., location: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., geometry: _Optional[str] = ..., instructions: _Optional[_Iterable[_Union[InstructionData, _Mapping]]] = ..., is_built: bool = ..., is_planned: bool = ..., elements_held: _Optional[_Iterable[str]] = ..., priority: _Optional[int] = ...) -> None: ...

class BuildingPlanData(_message.Message):
    __slots__ = ("guid", "name", "steps")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    steps: _containers.RepeatedCompositeFieldContainer[StepData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., steps: _Optional[_Iterable[_Union[StepData, _Mapping]]] = ...) -> None: ...

class NestedElementDataData(_message.Message):
    __slots__ = ("guid", "name", "frame", "key", "length")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    frame: _geometry_pb2.FrameData
    key: str
    length: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., key: _Optional[str] = ..., length: _Optional[float] = ...) -> None: ...

class BeamStockData(_message.Message):
    __slots__ = ("guid", "name", "spacing", "element_data", "cross_section", "length")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SPACING_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_DATA_FIELD_NUMBER: _ClassVar[int]
    CROSS_SECTION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    spacing: float
    element_data: _containers.RepeatedCompositeFieldContainer[NestedElementDataData]
    cross_section: _containers.RepeatedScalarFieldContainer[float]
    length: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., spacing: _Optional[float] = ..., element_data: _Optional[_Iterable[_Union[NestedElementDataData, _Mapping]]] = ..., cross_section: _Optional[_Iterable[float]] = ..., length: _Optional[float] = ...) -> None: ...

class PlateStockData(_message.Message):
    __slots__ = ("guid", "name", "spacing", "element_data", "dimensions", "thickness")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SPACING_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_DATA_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_FIELD_NUMBER: _ClassVar[int]
    THICKNESS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    spacing: float
    element_data: _containers.RepeatedCompositeFieldContainer[NestedElementDataData]
    dimensions: _containers.RepeatedScalarFieldContainer[float]
    thickness: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., spacing: _Optional[float] = ..., element_data: _Optional[_Iterable[_Union[NestedElementDataData, _Mapping]]] = ..., dimensions: _Optional[_Iterable[float]] = ..., thickness: _Optional[float] = ...) -> None: ...

class StockData(_message.Message):
    __slots__ = ("beam_stock", "plate_stock")
    BEAM_STOCK_FIELD_NUMBER: _ClassVar[int]
    PLATE_STOCK_FIELD_NUMBER: _ClassVar[int]
    beam_stock: BeamStockData
    plate_stock: PlateStockData
    def __init__(self, beam_stock: _Optional[_Union[BeamStockData, _Mapping]] = ..., plate_stock: _Optional[_Union[PlateStockData, _Mapping]] = ...) -> None: ...

class NestingResultData(_message.Message):
    __slots__ = ("guid", "name", "stocks", "tolerance")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STOCKS_FIELD_NUMBER: _ClassVar[int]
    TOLERANCE_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    stocks: _containers.RepeatedCompositeFieldContainer[StockData]
    tolerance: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., stocks: _Optional[_Iterable[_Union[StockData, _Mapping]]] = ..., tolerance: _Optional[float] = ...) -> None: ...
