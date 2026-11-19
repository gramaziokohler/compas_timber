from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_pb.generated import message_pb2 as _message_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from compas_timber.proto import fabrication_pb2 as _fabrication_pb2
from compas_timber.proto import panel_features_pb2 as _panel_features_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PlateGeometryData(_message.Message):
    __slots__ = ("guid", "name", "local_outline_a", "local_outline_b", "length", "width", "thickness")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOCAL_OUTLINE_A_FIELD_NUMBER: _ClassVar[int]
    LOCAL_OUTLINE_B_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    THICKNESS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    local_outline_a: _geometry_pb2.PolylineData
    local_outline_b: _geometry_pb2.PolylineData
    length: float
    width: float
    thickness: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., local_outline_a: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., local_outline_b: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., thickness: _Optional[float] = ...) -> None: ...

class LayerDefinitionData(_message.Message):
    __slots__ = ("guid", "name", "thickness", "sublayer_defs")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    THICKNESS_FIELD_NUMBER: _ClassVar[int]
    SUBLAYER_DEFS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    thickness: float
    sublayer_defs: _containers.RepeatedCompositeFieldContainer[LayerDefinitionData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., thickness: _Optional[float] = ..., sublayer_defs: _Optional[_Iterable[_Union[LayerDefinitionData, _Mapping]]] = ...) -> None: ...

class LayerStructureData(_message.Message):
    __slots__ = ("guid", "name", "layer_defs")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAYER_DEFS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    layer_defs: _containers.RepeatedCompositeFieldContainer[LayerDefinitionData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., layer_defs: _Optional[_Iterable[_Union[LayerDefinitionData, _Mapping]]] = ...) -> None: ...

class LayerPath(_message.Message):
    __slots__ = ("indices",)
    INDICES_FIELD_NUMBER: _ClassVar[int]
    indices: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, indices: _Optional[_Iterable[int]] = ...) -> None: ...

class LayerData(_message.Message):
    __slots__ = ("guid", "name", "plate_geometry", "start_offset", "layer_path", "frame")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PLATE_GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    START_OFFSET_FIELD_NUMBER: _ClassVar[int]
    LAYER_PATH_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    plate_geometry: PlateGeometryData
    start_offset: float
    layer_path: LayerPath
    frame: _geometry_pb2.FrameData
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., plate_geometry: _Optional[_Union[PlateGeometryData, _Mapping]] = ..., start_offset: _Optional[float] = ..., layer_path: _Optional[_Union[LayerPath, _Mapping]] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ...) -> None: ...

class BeamData(_message.Message):
    __slots__ = ("guid", "name", "frame", "length", "width", "height", "features", "attributes")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    frame: _geometry_pb2.FrameData
    length: float
    width: float
    height: float
    features: _containers.RepeatedCompositeFieldContainer[_fabrication_pb2.BTLxProcessingData]
    attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., features: _Optional[_Iterable[_Union[_fabrication_pb2.BTLxProcessingData, _Mapping]]] = ..., attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ...) -> None: ...

class PlateData(_message.Message):
    __slots__ = ("guid", "name", "plate_geometry", "features", "attributes", "frame")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PLATE_GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    plate_geometry: PlateGeometryData
    features: _containers.RepeatedCompositeFieldContainer[_fabrication_pb2.BTLxProcessingData]
    attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    frame: _geometry_pb2.FrameData
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., plate_geometry: _Optional[_Union[PlateGeometryData, _Mapping]] = ..., features: _Optional[_Iterable[_Union[_fabrication_pb2.BTLxProcessingData, _Mapping]]] = ..., attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ...) -> None: ...

class PanelData(_message.Message):
    __slots__ = ("guid", "name", "plate_geometry", "type", "features", "layer_structure", "attributes", "frame")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PLATE_GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    LAYER_STRUCTURE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    plate_geometry: PlateGeometryData
    type: str
    features: _containers.RepeatedCompositeFieldContainer[_panel_features_pb2.PanelFeatureData]
    layer_structure: LayerStructureData
    attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    frame: _geometry_pb2.FrameData
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., plate_geometry: _Optional[_Union[PlateGeometryData, _Mapping]] = ..., type: _Optional[str] = ..., features: _Optional[_Iterable[_Union[_panel_features_pb2.PanelFeatureData, _Mapping]]] = ..., layer_structure: _Optional[_Union[LayerStructureData, _Mapping]] = ..., attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ...) -> None: ...

class FastenerHoleData(_message.Message):
    __slots__ = ("point", "diameter", "vector", "through", "extra")
    class ExtraEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    POINT_FIELD_NUMBER: _ClassVar[int]
    DIAMETER_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    THROUGH_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    point: _geometry_pb2.PointData
    diameter: float
    vector: _geometry_pb2.VectorData
    through: bool
    extra: _containers.MessageMap[str, _message_pb2.AnyData]
    def __init__(self, point: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., diameter: _Optional[float] = ..., vector: _Optional[_Union[_geometry_pb2.VectorData, _Mapping]] = ..., through: bool = ..., extra: _Optional[_Mapping[str, _message_pb2.AnyData]] = ...) -> None: ...

class FastenerTimberInterfaceData(_message.Message):
    __slots__ = ("guid", "name", "outline_points", "thickness", "holes", "frame", "element_guid", "shapes", "features")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    OUTLINE_POINTS_FIELD_NUMBER: _ClassVar[int]
    THICKNESS_FIELD_NUMBER: _ClassVar[int]
    HOLES_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUID_FIELD_NUMBER: _ClassVar[int]
    SHAPES_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    outline_points: _common_pb2.PointList
    thickness: float
    holes: _containers.RepeatedCompositeFieldContainer[FastenerHoleData]
    frame: _geometry_pb2.FrameData
    element_guid: _common_pb2.GuidRef
    shapes: _containers.RepeatedCompositeFieldContainer[_message_pb2.AnyData]
    features: _containers.RepeatedCompositeFieldContainer[_fabrication_pb2.BTLxFromGeometryDefinitionData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., outline_points: _Optional[_Union[_common_pb2.PointList, _Mapping]] = ..., thickness: _Optional[float] = ..., holes: _Optional[_Iterable[_Union[FastenerHoleData, _Mapping]]] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., element_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., shapes: _Optional[_Iterable[_Union[_message_pb2.AnyData, _Mapping]]] = ..., features: _Optional[_Iterable[_Union[_fabrication_pb2.BTLxFromGeometryDefinitionData, _Mapping]]] = ...) -> None: ...

class FastenerData(_message.Message):
    __slots__ = ("guid", "name", "shape", "transformation", "interfaces")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMATION_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    shape: _message_pb2.AnyData
    transformation: _geometry_pb2.TransformationData
    interfaces: _containers.RepeatedCompositeFieldContainer[FastenerTimberInterfaceData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., shape: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ..., transformation: _Optional[_Union[_geometry_pb2.TransformationData, _Mapping]] = ..., interfaces: _Optional[_Iterable[_Union[FastenerTimberInterfaceData, _Mapping]]] = ...) -> None: ...

class BallNodeFastenerData(_message.Message):
    __slots__ = ("guid", "name", "shape", "transformation", "interfaces")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMATION_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    shape: _message_pb2.AnyData
    transformation: _geometry_pb2.TransformationData
    interfaces: _containers.RepeatedCompositeFieldContainer[FastenerTimberInterfaceData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., shape: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ..., transformation: _Optional[_Union[_geometry_pb2.TransformationData, _Mapping]] = ..., interfaces: _Optional[_Iterable[_Union[FastenerTimberInterfaceData, _Mapping]]] = ...) -> None: ...

class PlateFastenerData(_message.Message):
    __slots__ = ("guid", "name", "shape", "transformation", "outline", "thickness", "interfaces", "frame", "angle", "topology", "cutouts")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMATION_FIELD_NUMBER: _ClassVar[int]
    OUTLINE_FIELD_NUMBER: _ClassVar[int]
    THICKNESS_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    CUTOUTS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    shape: _message_pb2.AnyData
    transformation: _geometry_pb2.TransformationData
    outline: _geometry_pb2.PolylineData
    thickness: float
    interfaces: _containers.RepeatedCompositeFieldContainer[FastenerTimberInterfaceData]
    frame: _geometry_pb2.FrameData
    angle: float
    topology: str
    cutouts: _containers.RepeatedCompositeFieldContainer[_geometry_pb2.PolylineData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., shape: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ..., transformation: _Optional[_Union[_geometry_pb2.TransformationData, _Mapping]] = ..., outline: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., thickness: _Optional[float] = ..., interfaces: _Optional[_Iterable[_Union[FastenerTimberInterfaceData, _Mapping]]] = ..., frame: _Optional[_Union[_geometry_pb2.FrameData, _Mapping]] = ..., angle: _Optional[float] = ..., topology: _Optional[str] = ..., cutouts: _Optional[_Iterable[_Union[_geometry_pb2.PolylineData, _Mapping]]] = ...) -> None: ...

class GenericElementData(_message.Message):
    __slots__ = ("guid", "name", "transformation", "features", "material")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMATION_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    MATERIAL_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    transformation: _geometry_pb2.TransformationData
    features: _containers.RepeatedCompositeFieldContainer[_common_pb2.ModelFeatureData]
    material: _common_pb2.GuidRef
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., transformation: _Optional[_Union[_geometry_pb2.TransformationData, _Mapping]] = ..., features: _Optional[_Iterable[_Union[_common_pb2.ModelFeatureData, _Mapping]]] = ..., material: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ...) -> None: ...

class ElementData(_message.Message):
    __slots__ = ("beam", "plate", "panel", "layer", "fastener", "ball_node_fastener", "plate_fastener", "panel_feature", "generic_element")
    BEAM_FIELD_NUMBER: _ClassVar[int]
    PLATE_FIELD_NUMBER: _ClassVar[int]
    PANEL_FIELD_NUMBER: _ClassVar[int]
    LAYER_FIELD_NUMBER: _ClassVar[int]
    FASTENER_FIELD_NUMBER: _ClassVar[int]
    BALL_NODE_FASTENER_FIELD_NUMBER: _ClassVar[int]
    PLATE_FASTENER_FIELD_NUMBER: _ClassVar[int]
    PANEL_FEATURE_FIELD_NUMBER: _ClassVar[int]
    GENERIC_ELEMENT_FIELD_NUMBER: _ClassVar[int]
    beam: BeamData
    plate: PlateData
    panel: PanelData
    layer: LayerData
    fastener: FastenerData
    ball_node_fastener: BallNodeFastenerData
    plate_fastener: PlateFastenerData
    panel_feature: _panel_features_pb2.PanelFeatureData
    generic_element: GenericElementData
    def __init__(self, beam: _Optional[_Union[BeamData, _Mapping]] = ..., plate: _Optional[_Union[PlateData, _Mapping]] = ..., panel: _Optional[_Union[PanelData, _Mapping]] = ..., layer: _Optional[_Union[LayerData, _Mapping]] = ..., fastener: _Optional[_Union[FastenerData, _Mapping]] = ..., ball_node_fastener: _Optional[_Union[BallNodeFastenerData, _Mapping]] = ..., plate_fastener: _Optional[_Union[PlateFastenerData, _Mapping]] = ..., panel_feature: _Optional[_Union[_panel_features_pb2.PanelFeatureData, _Mapping]] = ..., generic_element: _Optional[_Union[GenericElementData, _Mapping]] = ...) -> None: ...
