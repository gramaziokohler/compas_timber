from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_pb.generated import message_pb2 as _message_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from compas_timber.proto import elements_pb2 as _elements_pb2
from compas_timber.proto import panel_features_pb2 as _panel_features_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CutPlaneSpecData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "angle", "offset")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    angle: float
    offset: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., angle: _Optional[float] = ..., offset: _Optional[float] = ...) -> None: ...

class MiterPlaneSpecData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "angle_x", "angle_y", "offset")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    ANGLE_X_FIELD_NUMBER: _ClassVar[int]
    ANGLE_Y_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    angle_x: float
    angle_y: float
    offset: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., angle_x: _Optional[float] = ..., angle_y: _Optional[float] = ..., offset: _Optional[float] = ...) -> None: ...

class JointCandidateData(_message.Message):
    __slots__ = ("guid", "name", "element_guids", "topology", "location", "distance", "extra_kwargs")
    class ExtraKwargsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    EXTRA_KWARGS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    topology: int
    location: _geometry_pb2.PointData
    distance: float
    extra_kwargs: _containers.MessageMap[str, _message_pb2.AnyData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., distance: _Optional[float] = ..., extra_kwargs: _Optional[_Mapping[str, _message_pb2.AnyData]] = ...) -> None: ...

class BeamSolverResultData(_message.Message):
    __slots__ = ("guid", "name", "topology", "beam_a_guid", "beam_b_guid", "distance", "location")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    BEAM_A_GUID_FIELD_NUMBER: _ClassVar[int]
    BEAM_B_GUID_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    beam_a_guid: _common_pb2.GuidRef
    beam_b_guid: _common_pb2.GuidRef
    distance: float
    location: _geometry_pb2.PointData
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., beam_a_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., beam_b_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., distance: _Optional[float] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ...) -> None: ...

class PlateSolverResultData(_message.Message):
    __slots__ = ("guid", "name", "topology", "plate_a_guid", "plate_b_guid", "a_segment_index", "b_segment_index", "distance", "location")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    PLATE_A_GUID_FIELD_NUMBER: _ClassVar[int]
    PLATE_B_GUID_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    plate_a_guid: _common_pb2.GuidRef
    plate_b_guid: _common_pb2.GuidRef
    a_segment_index: int
    b_segment_index: int
    distance: float
    location: _geometry_pb2.PointData
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., plate_a_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., plate_b_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ..., distance: _Optional[float] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ...) -> None: ...

class BallNodeJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "beam_guids", "ball_diameter", "fastener_guid", "base_interface")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    BEAM_GUIDS_FIELD_NUMBER: _ClassVar[int]
    BALL_DIAMETER_FIELD_NUMBER: _ClassVar[int]
    FASTENER_GUID_FIELD_NUMBER: _ClassVar[int]
    BASE_INTERFACE_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    beam_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    ball_diameter: float
    fastener_guid: _common_pb2.GuidRef
    base_interface: _elements_pb2.FastenerTimberInterfaceData
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., beam_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., ball_diameter: _Optional[float] = ..., fastener_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., base_interface: _Optional[_Union[_elements_pb2.FastenerTimberInterfaceData, _Mapping]] = ...) -> None: ...

class ButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "mill_depth", "butt_plane_spec", "force_pocket", "conical_tool")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    MILL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    BUTT_PLANE_SPEC_FIELD_NUMBER: _ClassVar[int]
    FORCE_POCKET_FIELD_NUMBER: _ClassVar[int]
    CONICAL_TOOL_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    mill_depth: float
    butt_plane_spec: CutPlaneSpecData
    force_pocket: bool
    conical_tool: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., mill_depth: _Optional[float] = ..., butt_plane_spec: _Optional[_Union[CutPlaneSpecData, _Mapping]] = ..., force_pocket: bool = ..., conical_tool: bool = ...) -> None: ...

class CompositeJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "joints")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    JOINTS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    joints: _containers.RepeatedCompositeFieldContainer[JointData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., joints: _Optional[_Iterable[_Union[JointData, _Mapping]]] = ...) -> None: ...

class ISimpleScarfData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "main_beam_guid", "cross_beam_guid", "length", "depth_ref_side", "depth_opp_side", "num_drill_hole", "drill_hole_diam", "ref_side_index")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    MAIN_BEAM_GUID_FIELD_NUMBER: _ClassVar[int]
    CROSS_BEAM_GUID_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_REF_SIDE_FIELD_NUMBER: _ClassVar[int]
    DEPTH_OPP_SIDE_FIELD_NUMBER: _ClassVar[int]
    NUM_DRILL_HOLE_FIELD_NUMBER: _ClassVar[int]
    DRILL_HOLE_DIAM_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    main_beam_guid: _common_pb2.GuidRef
    cross_beam_guid: _common_pb2.GuidRef
    length: float
    depth_ref_side: float
    depth_opp_side: float
    num_drill_hole: int
    drill_hole_diam: float
    ref_side_index: int
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., main_beam_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., cross_beam_guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., length: _Optional[float] = ..., depth_ref_side: _Optional[float] = ..., depth_opp_side: _Optional[float] = ..., num_drill_hole: _Optional[int] = ..., drill_hole_diam: _Optional[float] = ..., ref_side_index: _Optional[int] = ...) -> None: ...

class LButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "mill_depth", "butt_plane_spec", "force_pocket", "conical_tool", "back_plane_spec", "modify_cross", "reject_i")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    MILL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    BUTT_PLANE_SPEC_FIELD_NUMBER: _ClassVar[int]
    FORCE_POCKET_FIELD_NUMBER: _ClassVar[int]
    CONICAL_TOOL_FIELD_NUMBER: _ClassVar[int]
    BACK_PLANE_SPEC_FIELD_NUMBER: _ClassVar[int]
    MODIFY_CROSS_FIELD_NUMBER: _ClassVar[int]
    REJECT_I_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    mill_depth: float
    butt_plane_spec: CutPlaneSpecData
    force_pocket: bool
    conical_tool: bool
    back_plane_spec: CutPlaneSpecData
    modify_cross: bool
    reject_i: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., mill_depth: _Optional[float] = ..., butt_plane_spec: _Optional[_Union[CutPlaneSpecData, _Mapping]] = ..., force_pocket: bool = ..., conical_tool: bool = ..., back_plane_spec: _Optional[_Union[CutPlaneSpecData, _Mapping]] = ..., modify_cross: bool = ..., reject_i: bool = ...) -> None: ...

class LFrenchRidgeLapJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "flip_lap_side", "drillhole_diam")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    FLIP_LAP_SIDE_FIELD_NUMBER: _ClassVar[int]
    DRILLHOLE_DIAM_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    flip_lap_side: bool
    drillhole_diam: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., flip_lap_side: bool = ..., drillhole_diam: _Optional[float] = ...) -> None: ...

class LLapJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "flip_lap_side", "cut_plane_bias")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    FLIP_LAP_SIDE_FIELD_NUMBER: _ClassVar[int]
    CUT_PLANE_BIAS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    flip_lap_side: bool
    cut_plane_bias: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., flip_lap_side: bool = ..., cut_plane_bias: _Optional[float] = ...) -> None: ...

class LMiterJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "cutoff", "ref_side_miter", "miter_plane", "clean")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    CUTOFF_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_MITER_FIELD_NUMBER: _ClassVar[int]
    MITER_PLANE_FIELD_NUMBER: _ClassVar[int]
    CLEAN_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    cutoff: bool
    ref_side_miter: bool
    miter_plane: MiterPlaneSpecData
    clean: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., cutoff: bool = ..., ref_side_miter: bool = ..., miter_plane: _Optional[_Union[MiterPlaneSpecData, _Mapping]] = ..., clean: bool = ...) -> None: ...

class LTenonMortiseJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "start_y", "start_depth", "rotation", "length", "width", "height", "tenon_shape", "shape_radius", "modify_cross")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TENON_SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    MODIFY_CROSS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    start_y: float
    start_depth: float
    rotation: float
    length: float
    width: float
    height: float
    tenon_shape: str
    shape_radius: float
    modify_cross: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., rotation: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., tenon_shape: _Optional[str] = ..., shape_radius: _Optional[float] = ..., modify_cross: bool = ...) -> None: ...

class LapJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "flip_lap_side", "cut_plane_bias")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    FLIP_LAP_SIDE_FIELD_NUMBER: _ClassVar[int]
    CUT_PLANE_BIAS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    flip_lap_side: bool
    cut_plane_bias: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., flip_lap_side: bool = ..., cut_plane_bias: _Optional[float] = ...) -> None: ...

class MortiseTenonJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "start_y", "start_depth", "rotation", "length", "width", "height", "tenon_shape", "shape_radius")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TENON_SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    start_y: float
    start_depth: float
    rotation: float
    length: float
    width: float
    height: float
    tenon_shape: str
    shape_radius: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., rotation: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., tenon_shape: _Optional[str] = ..., shape_radius: _Optional[float] = ...) -> None: ...

class PanelLButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index", "interfaces")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    interfaces: _containers.RepeatedCompositeFieldContainer[_panel_features_pb2.PanelConnectionInterfaceData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ..., interfaces: _Optional[_Iterable[_Union[_panel_features_pb2.PanelConnectionInterfaceData, _Mapping]]] = ...) -> None: ...

class PanelLLayerButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index", "interfaces")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    interfaces: _containers.RepeatedCompositeFieldContainer[_panel_features_pb2.PanelConnectionInterfaceData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ..., interfaces: _Optional[_Iterable[_Union[_panel_features_pb2.PanelConnectionInterfaceData, _Mapping]]] = ...) -> None: ...

class PanelMiterJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index", "interfaces")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    interfaces: _containers.RepeatedCompositeFieldContainer[_panel_features_pb2.PanelConnectionInterfaceData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ..., interfaces: _Optional[_Iterable[_Union[_panel_features_pb2.PanelConnectionInterfaceData, _Mapping]]] = ...) -> None: ...

class PanelTButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index", "interfaces")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    INTERFACES_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    interfaces: _containers.RepeatedCompositeFieldContainer[_panel_features_pb2.PanelConnectionInterfaceData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ..., interfaces: _Optional[_Iterable[_Union[_panel_features_pb2.PanelConnectionInterfaceData, _Mapping]]] = ...) -> None: ...

class PlateLButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ...) -> None: ...

class PlateMiterJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ...) -> None: ...

class PlateTButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "a_segment_index", "b_segment_index")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    A_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    B_SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    a_segment_index: int
    b_segment_index: int
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., a_segment_index: _Optional[int] = ..., b_segment_index: _Optional[int] = ...) -> None: ...

class TBirdsmouthJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "mill_depth")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    MILL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    mill_depth: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., mill_depth: _Optional[float] = ...) -> None: ...

class TButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "mill_depth", "butt_plane_spec", "force_pocket", "conical_tool")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    MILL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    BUTT_PLANE_SPEC_FIELD_NUMBER: _ClassVar[int]
    FORCE_POCKET_FIELD_NUMBER: _ClassVar[int]
    CONICAL_TOOL_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    mill_depth: float
    butt_plane_spec: CutPlaneSpecData
    force_pocket: bool
    conical_tool: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., mill_depth: _Optional[float] = ..., butt_plane_spec: _Optional[_Union[CutPlaneSpecData, _Mapping]] = ..., force_pocket: bool = ..., conical_tool: bool = ...) -> None: ...

class TDovetailJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "start_y", "start_depth", "rotation", "length", "width", "cone_angle", "dovetail_shape", "tool_angle", "tool_diameter", "tool_height")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    CONE_ANGLE_FIELD_NUMBER: _ClassVar[int]
    DOVETAIL_SHAPE_FIELD_NUMBER: _ClassVar[int]
    TOOL_ANGLE_FIELD_NUMBER: _ClassVar[int]
    TOOL_DIAMETER_FIELD_NUMBER: _ClassVar[int]
    TOOL_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    start_y: float
    start_depth: float
    rotation: float
    length: float
    width: float
    cone_angle: float
    dovetail_shape: str
    tool_angle: float
    tool_diameter: float
    tool_height: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., rotation: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., cone_angle: _Optional[float] = ..., dovetail_shape: _Optional[str] = ..., tool_angle: _Optional[float] = ..., tool_diameter: _Optional[float] = ..., tool_height: _Optional[float] = ...) -> None: ...

class TLapJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "flip_lap_side", "cut_plane_bias")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    FLIP_LAP_SIDE_FIELD_NUMBER: _ClassVar[int]
    CUT_PLANE_BIAS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    flip_lap_side: bool
    cut_plane_bias: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., flip_lap_side: bool = ..., cut_plane_bias: _Optional[float] = ...) -> None: ...

class TOliGinaJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "start_y", "start_depth", "rotation", "length", "width", "height", "tenon_shape", "shape_radius")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TENON_SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    start_y: float
    start_depth: float
    rotation: float
    length: float
    width: float
    height: float
    tenon_shape: str
    shape_radius: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., rotation: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., tenon_shape: _Optional[str] = ..., shape_radius: _Optional[float] = ...) -> None: ...

class TStepJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "step_shape", "step_depth", "heel_depth", "tenon_mortise_height")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    STEP_SHAPE_FIELD_NUMBER: _ClassVar[int]
    STEP_DEPTH_FIELD_NUMBER: _ClassVar[int]
    HEEL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    TENON_MORTISE_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    step_shape: str
    step_depth: float
    heel_depth: float
    tenon_mortise_height: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., step_shape: _Optional[str] = ..., step_depth: _Optional[float] = ..., heel_depth: _Optional[float] = ..., tenon_mortise_height: _Optional[float] = ...) -> None: ...

class TTenonMortiseJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "start_y", "start_depth", "rotation", "length", "width", "height", "tenon_shape", "shape_radius")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TENON_SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    start_y: float
    start_depth: float
    rotation: float
    length: float
    width: float
    height: float
    tenon_shape: str
    shape_radius: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., rotation: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., tenon_shape: _Optional[str] = ..., shape_radius: _Optional[float] = ...) -> None: ...

class XLapJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "flip_lap_side", "cut_plane_bias")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    FLIP_LAP_SIDE_FIELD_NUMBER: _ClassVar[int]
    CUT_PLANE_BIAS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    flip_lap_side: bool
    cut_plane_bias: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., flip_lap_side: bool = ..., cut_plane_bias: _Optional[float] = ...) -> None: ...

class XNotchJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ...) -> None: ...

class YButtJointData(_message.Message):
    __slots__ = ("guid", "name", "topology", "location", "element_guids", "mill_depth")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TOPOLOGY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    MILL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    topology: int
    location: _geometry_pb2.PointData
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    mill_depth: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., topology: _Optional[int] = ..., location: _Optional[_Union[_geometry_pb2.PointData, _Mapping]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., mill_depth: _Optional[float] = ...) -> None: ...

class JointData(_message.Message):
    __slots__ = ("ball_node_joint", "butt_joint", "composite_joint", "i_simple_scarf", "l_butt_joint", "l_french_ridge_lap_joint", "l_lap_joint", "l_miter_joint", "l_tenon_mortise_joint", "lap_joint", "mortise_tenon_joint", "panel_l_butt_joint", "panel_l_layer_butt_joint", "panel_miter_joint", "panel_t_butt_joint", "plate_l_butt_joint", "plate_miter_joint", "plate_t_butt_joint", "t_birdsmouth_joint", "t_butt_joint", "t_dovetail_joint", "t_lap_joint", "t_oli_gina_joint", "t_step_joint", "t_tenon_mortise_joint", "x_lap_joint", "x_notch_joint", "y_butt_joint")
    BALL_NODE_JOINT_FIELD_NUMBER: _ClassVar[int]
    BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    COMPOSITE_JOINT_FIELD_NUMBER: _ClassVar[int]
    I_SIMPLE_SCARF_FIELD_NUMBER: _ClassVar[int]
    L_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    L_FRENCH_RIDGE_LAP_JOINT_FIELD_NUMBER: _ClassVar[int]
    L_LAP_JOINT_FIELD_NUMBER: _ClassVar[int]
    L_MITER_JOINT_FIELD_NUMBER: _ClassVar[int]
    L_TENON_MORTISE_JOINT_FIELD_NUMBER: _ClassVar[int]
    LAP_JOINT_FIELD_NUMBER: _ClassVar[int]
    MORTISE_TENON_JOINT_FIELD_NUMBER: _ClassVar[int]
    PANEL_L_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    PANEL_L_LAYER_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    PANEL_MITER_JOINT_FIELD_NUMBER: _ClassVar[int]
    PANEL_T_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    PLATE_L_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    PLATE_MITER_JOINT_FIELD_NUMBER: _ClassVar[int]
    PLATE_T_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_BIRDSMOUTH_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_DOVETAIL_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_LAP_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_OLI_GINA_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_STEP_JOINT_FIELD_NUMBER: _ClassVar[int]
    T_TENON_MORTISE_JOINT_FIELD_NUMBER: _ClassVar[int]
    X_LAP_JOINT_FIELD_NUMBER: _ClassVar[int]
    X_NOTCH_JOINT_FIELD_NUMBER: _ClassVar[int]
    Y_BUTT_JOINT_FIELD_NUMBER: _ClassVar[int]
    ball_node_joint: BallNodeJointData
    butt_joint: ButtJointData
    composite_joint: CompositeJointData
    i_simple_scarf: ISimpleScarfData
    l_butt_joint: LButtJointData
    l_french_ridge_lap_joint: LFrenchRidgeLapJointData
    l_lap_joint: LLapJointData
    l_miter_joint: LMiterJointData
    l_tenon_mortise_joint: LTenonMortiseJointData
    lap_joint: LapJointData
    mortise_tenon_joint: MortiseTenonJointData
    panel_l_butt_joint: PanelLButtJointData
    panel_l_layer_butt_joint: PanelLLayerButtJointData
    panel_miter_joint: PanelMiterJointData
    panel_t_butt_joint: PanelTButtJointData
    plate_l_butt_joint: PlateLButtJointData
    plate_miter_joint: PlateMiterJointData
    plate_t_butt_joint: PlateTButtJointData
    t_birdsmouth_joint: TBirdsmouthJointData
    t_butt_joint: TButtJointData
    t_dovetail_joint: TDovetailJointData
    t_lap_joint: TLapJointData
    t_oli_gina_joint: TOliGinaJointData
    t_step_joint: TStepJointData
    t_tenon_mortise_joint: TTenonMortiseJointData
    x_lap_joint: XLapJointData
    x_notch_joint: XNotchJointData
    y_butt_joint: YButtJointData
    def __init__(self, ball_node_joint: _Optional[_Union[BallNodeJointData, _Mapping]] = ..., butt_joint: _Optional[_Union[ButtJointData, _Mapping]] = ..., composite_joint: _Optional[_Union[CompositeJointData, _Mapping]] = ..., i_simple_scarf: _Optional[_Union[ISimpleScarfData, _Mapping]] = ..., l_butt_joint: _Optional[_Union[LButtJointData, _Mapping]] = ..., l_french_ridge_lap_joint: _Optional[_Union[LFrenchRidgeLapJointData, _Mapping]] = ..., l_lap_joint: _Optional[_Union[LLapJointData, _Mapping]] = ..., l_miter_joint: _Optional[_Union[LMiterJointData, _Mapping]] = ..., l_tenon_mortise_joint: _Optional[_Union[LTenonMortiseJointData, _Mapping]] = ..., lap_joint: _Optional[_Union[LapJointData, _Mapping]] = ..., mortise_tenon_joint: _Optional[_Union[MortiseTenonJointData, _Mapping]] = ..., panel_l_butt_joint: _Optional[_Union[PanelLButtJointData, _Mapping]] = ..., panel_l_layer_butt_joint: _Optional[_Union[PanelLLayerButtJointData, _Mapping]] = ..., panel_miter_joint: _Optional[_Union[PanelMiterJointData, _Mapping]] = ..., panel_t_butt_joint: _Optional[_Union[PanelTButtJointData, _Mapping]] = ..., plate_l_butt_joint: _Optional[_Union[PlateLButtJointData, _Mapping]] = ..., plate_miter_joint: _Optional[_Union[PlateMiterJointData, _Mapping]] = ..., plate_t_butt_joint: _Optional[_Union[PlateTButtJointData, _Mapping]] = ..., t_birdsmouth_joint: _Optional[_Union[TBirdsmouthJointData, _Mapping]] = ..., t_butt_joint: _Optional[_Union[TButtJointData, _Mapping]] = ..., t_dovetail_joint: _Optional[_Union[TDovetailJointData, _Mapping]] = ..., t_lap_joint: _Optional[_Union[TLapJointData, _Mapping]] = ..., t_oli_gina_joint: _Optional[_Union[TOliGinaJointData, _Mapping]] = ..., t_step_joint: _Optional[_Union[TStepJointData, _Mapping]] = ..., t_tenon_mortise_joint: _Optional[_Union[TTenonMortiseJointData, _Mapping]] = ..., x_lap_joint: _Optional[_Union[XLapJointData, _Mapping]] = ..., x_notch_joint: _Optional[_Union[XNotchJointData, _Mapping]] = ..., y_butt_joint: _Optional[_Union[YButtJointData, _Mapping]] = ...) -> None: ...
