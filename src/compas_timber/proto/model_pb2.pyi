from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_pb.generated import message_pb2 as _message_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from compas_timber.proto import elements_pb2 as _elements_pb2
from compas_timber.proto import connections_pb2 as _connections_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MaterialData(_message.Message):
    __slots__ = ("guid", "name")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ...) -> None: ...

class TimberMaterialData(_message.Message):
    __slots__ = ("guid", "name")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ...) -> None: ...

class ConcreteData(_message.Message):
    __slots__ = ("guid", "name", "fck", "fck_cube", "fcm", "fctm", "Ecm", "density", "poisson")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FCK_FIELD_NUMBER: _ClassVar[int]
    FCK_CUBE_FIELD_NUMBER: _ClassVar[int]
    FCM_FIELD_NUMBER: _ClassVar[int]
    FCTM_FIELD_NUMBER: _ClassVar[int]
    ECM_FIELD_NUMBER: _ClassVar[int]
    DENSITY_FIELD_NUMBER: _ClassVar[int]
    POISSON_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    fck: float
    fck_cube: float
    fcm: float
    fctm: float
    Ecm: float
    density: float
    poisson: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., fck: _Optional[float] = ..., fck_cube: _Optional[float] = ..., fcm: _Optional[float] = ..., fctm: _Optional[float] = ..., Ecm: _Optional[float] = ..., density: _Optional[float] = ..., poisson: _Optional[float] = ...) -> None: ...

class SteelData(_message.Message):
    __slots__ = ("guid", "name", "fy", "fu")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FY_FIELD_NUMBER: _ClassVar[int]
    FU_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    fy: float
    fu: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., fy: _Optional[float] = ..., fu: _Optional[float] = ...) -> None: ...

class ModelMaterialData(_message.Message):
    __slots__ = ("base_material", "timber", "concrete", "steel")
    BASE_MATERIAL_FIELD_NUMBER: _ClassVar[int]
    TIMBER_FIELD_NUMBER: _ClassVar[int]
    CONCRETE_FIELD_NUMBER: _ClassVar[int]
    STEEL_FIELD_NUMBER: _ClassVar[int]
    base_material: MaterialData
    timber: TimberMaterialData
    concrete: ConcreteData
    steel: SteelData
    def __init__(self, base_material: _Optional[_Union[MaterialData, _Mapping]] = ..., timber: _Optional[_Union[TimberMaterialData, _Mapping]] = ..., concrete: _Optional[_Union[ConcreteData, _Mapping]] = ..., steel: _Optional[_Union[SteelData, _Mapping]] = ...) -> None: ...

class ElementTreeData(_message.Message):
    __slots__ = ("attributes", "parent", "name_table", "node_name_refs", "node_elements", "node_attr_indices", "node_attr_values")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    PARENT_FIELD_NUMBER: _ClassVar[int]
    NAME_TABLE_FIELD_NUMBER: _ClassVar[int]
    NODE_NAME_REFS_FIELD_NUMBER: _ClassVar[int]
    NODE_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    NODE_ATTR_INDICES_FIELD_NUMBER: _ClassVar[int]
    NODE_ATTR_VALUES_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    parent: _containers.RepeatedScalarFieldContainer[int]
    name_table: _containers.RepeatedScalarFieldContainer[str]
    node_name_refs: _containers.RepeatedScalarFieldContainer[int]
    node_elements: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    node_attr_indices: _containers.RepeatedScalarFieldContainer[int]
    node_attr_values: _containers.RepeatedCompositeFieldContainer[_message_pb2.DictData]
    def __init__(self, attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ..., parent: _Optional[_Iterable[int]] = ..., name_table: _Optional[_Iterable[str]] = ..., node_name_refs: _Optional[_Iterable[int]] = ..., node_elements: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., node_attr_indices: _Optional[_Iterable[int]] = ..., node_attr_values: _Optional[_Iterable[_Union[_message_pb2.DictData, _Mapping]]] = ...) -> None: ...

class InteractionGraphData(_message.Message):
    __slots__ = ("attributes", "default_node_attributes", "default_edge_attributes", "max_node", "node_keys", "node_elements", "node_attr_indices", "node_attr_values", "edge_u", "edge_v", "edge_joints", "edge_attr_indices", "edge_attr_values")
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    class DefaultNodeAttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    class DefaultEdgeAttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_NODE_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_EDGE_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    MAX_NODE_FIELD_NUMBER: _ClassVar[int]
    NODE_KEYS_FIELD_NUMBER: _ClassVar[int]
    NODE_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    NODE_ATTR_INDICES_FIELD_NUMBER: _ClassVar[int]
    NODE_ATTR_VALUES_FIELD_NUMBER: _ClassVar[int]
    EDGE_U_FIELD_NUMBER: _ClassVar[int]
    EDGE_V_FIELD_NUMBER: _ClassVar[int]
    EDGE_JOINTS_FIELD_NUMBER: _ClassVar[int]
    EDGE_ATTR_INDICES_FIELD_NUMBER: _ClassVar[int]
    EDGE_ATTR_VALUES_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    default_node_attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    default_edge_attributes: _containers.MessageMap[str, _message_pb2.AnyData]
    max_node: int
    node_keys: _containers.RepeatedScalarFieldContainer[int]
    node_elements: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    node_attr_indices: _containers.RepeatedScalarFieldContainer[int]
    node_attr_values: _containers.RepeatedCompositeFieldContainer[_message_pb2.DictData]
    edge_u: _containers.RepeatedScalarFieldContainer[int]
    edge_v: _containers.RepeatedScalarFieldContainer[int]
    edge_joints: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    edge_attr_indices: _containers.RepeatedScalarFieldContainer[int]
    edge_attr_values: _containers.RepeatedCompositeFieldContainer[_message_pb2.DictData]
    def __init__(self, attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ..., default_node_attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ..., default_edge_attributes: _Optional[_Mapping[str, _message_pb2.AnyData]] = ..., max_node: _Optional[int] = ..., node_keys: _Optional[_Iterable[int]] = ..., node_elements: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., node_attr_indices: _Optional[_Iterable[int]] = ..., node_attr_values: _Optional[_Iterable[_Union[_message_pb2.DictData, _Mapping]]] = ..., edge_u: _Optional[_Iterable[int]] = ..., edge_v: _Optional[_Iterable[int]] = ..., edge_joints: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., edge_attr_indices: _Optional[_Iterable[int]] = ..., edge_attr_values: _Optional[_Iterable[_Union[_message_pb2.DictData, _Mapping]]] = ...) -> None: ...

class TimberModelData(_message.Message):
    __slots__ = ("guid", "name", "guid_table", "transformation", "elements", "materials", "tree", "graph", "joints")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    GUID_TABLE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    MATERIALS_FIELD_NUMBER: _ClassVar[int]
    TREE_FIELD_NUMBER: _ClassVar[int]
    GRAPH_FIELD_NUMBER: _ClassVar[int]
    JOINTS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    guid_table: _containers.RepeatedScalarFieldContainer[bytes]
    transformation: _geometry_pb2.TransformationData
    elements: _containers.RepeatedCompositeFieldContainer[_elements_pb2.ElementData]
    materials: _containers.RepeatedCompositeFieldContainer[ModelMaterialData]
    tree: ElementTreeData
    graph: InteractionGraphData
    joints: _containers.RepeatedCompositeFieldContainer[_connections_pb2.JointData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., guid_table: _Optional[_Iterable[bytes]] = ..., transformation: _Optional[_Union[_geometry_pb2.TransformationData, _Mapping]] = ..., elements: _Optional[_Iterable[_Union[_elements_pb2.ElementData, _Mapping]]] = ..., materials: _Optional[_Iterable[_Union[ModelMaterialData, _Mapping]]] = ..., tree: _Optional[_Union[ElementTreeData, _Mapping]] = ..., graph: _Optional[_Union[InteractionGraphData, _Mapping]] = ..., joints: _Optional[_Iterable[_Union[_connections_pb2.JointData, _Mapping]]] = ...) -> None: ...
