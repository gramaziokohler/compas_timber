from compas_pb.generated import geometry_pb2 as _geometry_pb2
from compas_pb.generated import message_pb2 as _message_pb2
from compas_timber.proto import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ContourData(_message.Message):
    __slots__ = ("guid", "name", "polyline", "depth", "depth_bounded", "inclination")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    POLYLINE_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_BOUNDED_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    polyline: _geometry_pb2.PolylineData
    depth: float
    depth_bounded: bool
    inclination: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., polyline: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., depth: _Optional[float] = ..., depth_bounded: bool = ..., inclination: _Optional[_Iterable[float]] = ...) -> None: ...

class DualContourData(_message.Message):
    __slots__ = ("guid", "name", "principal_contour", "associated_contour", "depth_bounded")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRINCIPAL_CONTOUR_FIELD_NUMBER: _ClassVar[int]
    ASSOCIATED_CONTOUR_FIELD_NUMBER: _ClassVar[int]
    DEPTH_BOUNDED_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    principal_contour: _geometry_pb2.PolylineData
    associated_contour: _geometry_pb2.PolylineData
    depth_bounded: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., principal_contour: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., associated_contour: _Optional[_Union[_geometry_pb2.PolylineData, _Mapping]] = ..., depth_bounded: bool = ...) -> None: ...

class JackRafterCutData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "start_depth", "angle", "inclination")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    inclination: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ...) -> None: ...

class DoubleCutData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "angle_1", "inclination_1", "angle_2", "inclination_2")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    ANGLE_1_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_1_FIELD_NUMBER: _ClassVar[int]
    ANGLE_2_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_2_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    angle_1: float
    inclination_1: float
    angle_2: float
    inclination_2: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., angle_1: _Optional[float] = ..., inclination_1: _Optional[float] = ..., angle_2: _Optional[float] = ..., inclination_2: _Optional[float] = ...) -> None: ...

class DrillingData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "start_x", "start_y", "angle", "inclination", "depth_limited", "depth", "diameter")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    DEPTH_LIMITED_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    DIAMETER_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    start_x: float
    start_y: float
    angle: float
    inclination: float
    depth_limited: bool
    depth: float
    diameter: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ..., depth_limited: bool = ..., depth: _Optional[float] = ..., diameter: _Optional[float] = ...) -> None: ...

class LapData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "angle", "inclination", "slope", "length", "width", "depth", "lead_angle_parallel", "lead_angle", "lead_inclination_parallel", "lead_inclination", "machining_limits")
    class MachiningLimitsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    SLOPE_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    LEAD_ANGLE_PARALLEL_FIELD_NUMBER: _ClassVar[int]
    LEAD_ANGLE_FIELD_NUMBER: _ClassVar[int]
    LEAD_INCLINATION_PARALLEL_FIELD_NUMBER: _ClassVar[int]
    LEAD_INCLINATION_FIELD_NUMBER: _ClassVar[int]
    MACHINING_LIMITS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    angle: float
    inclination: float
    slope: float
    length: float
    width: float
    depth: float
    lead_angle_parallel: bool
    lead_angle: float
    lead_inclination_parallel: bool
    lead_inclination: float
    machining_limits: _containers.ScalarMap[str, bool]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ..., slope: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., depth: _Optional[float] = ..., lead_angle_parallel: bool = ..., lead_angle: _Optional[float] = ..., lead_inclination_parallel: bool = ..., lead_inclination: _Optional[float] = ..., machining_limits: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class MortiseData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "start_x", "start_y", "start_depth", "angle", "slope", "inclination", "length_limited_top", "length_limited_bottom", "length", "width", "depth", "shape", "shape_radius")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    SLOPE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_TOP_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_BOTTOM_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    slope: float
    inclination: float
    length_limited_top: bool
    length_limited_bottom: bool
    length: float
    width: float
    depth: float
    shape: str
    shape_radius: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., slope: _Optional[float] = ..., inclination: _Optional[float] = ..., length_limited_top: bool = ..., length_limited_bottom: bool = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., depth: _Optional[float] = ..., shape: _Optional[str] = ..., shape_radius: _Optional[float] = ...) -> None: ...

class TenonData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "start_depth", "angle", "inclination", "rotation", "length_limited_top", "length_limited_bottom", "length", "width", "height", "shape", "shape_radius", "chamfer")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_TOP_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_BOTTOM_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    CHAMFER_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    inclination: float
    rotation: float
    length_limited_top: bool
    length_limited_bottom: bool
    length: float
    width: float
    height: float
    shape: str
    shape_radius: float
    chamfer: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ..., rotation: _Optional[float] = ..., length_limited_top: bool = ..., length_limited_bottom: bool = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., shape: _Optional[str] = ..., shape_radius: _Optional[float] = ..., chamfer: bool = ...) -> None: ...

class PocketData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "start_x", "start_y", "start_depth", "angle", "inclination", "slope", "length", "width", "internal_angle", "tilt_ref_side", "tilt_end_side", "tilt_opp_side", "tilt_start_side", "machining_limits")
    class MachiningLimitsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    SLOPE_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    INTERNAL_ANGLE_FIELD_NUMBER: _ClassVar[int]
    TILT_REF_SIDE_FIELD_NUMBER: _ClassVar[int]
    TILT_END_SIDE_FIELD_NUMBER: _ClassVar[int]
    TILT_OPP_SIDE_FIELD_NUMBER: _ClassVar[int]
    TILT_START_SIDE_FIELD_NUMBER: _ClassVar[int]
    MACHINING_LIMITS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    inclination: float
    slope: float
    length: float
    width: float
    internal_angle: float
    tilt_ref_side: float
    tilt_end_side: float
    tilt_opp_side: float
    tilt_start_side: float
    machining_limits: _containers.ScalarMap[str, bool]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ..., slope: _Optional[float] = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., internal_angle: _Optional[float] = ..., tilt_ref_side: _Optional[float] = ..., tilt_end_side: _Optional[float] = ..., tilt_opp_side: _Optional[float] = ..., tilt_start_side: _Optional[float] = ..., machining_limits: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class SlotData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "start_depth", "angle", "inclination", "length", "depth", "thickness", "angle_ref_point", "angle_opp_point", "add_angle_opp_point", "machining_limits")
    class MachiningLimitsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    THICKNESS_FIELD_NUMBER: _ClassVar[int]
    ANGLE_REF_POINT_FIELD_NUMBER: _ClassVar[int]
    ANGLE_OPP_POINT_FIELD_NUMBER: _ClassVar[int]
    ADD_ANGLE_OPP_POINT_FIELD_NUMBER: _ClassVar[int]
    MACHINING_LIMITS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    inclination: float
    length: float
    depth: float
    thickness: float
    angle_ref_point: float
    angle_opp_point: float
    add_angle_opp_point: float
    machining_limits: _containers.ScalarMap[str, bool]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ..., length: _Optional[float] = ..., depth: _Optional[float] = ..., thickness: _Optional[float] = ..., angle_ref_point: _Optional[float] = ..., angle_opp_point: _Optional[float] = ..., add_angle_opp_point: _Optional[float] = ..., machining_limits: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class StepJointData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "strut_inclination", "step_depth", "heel_depth", "step_shape", "tenon", "tenon_width", "tenon_height")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    STRUT_INCLINATION_FIELD_NUMBER: _ClassVar[int]
    STEP_DEPTH_FIELD_NUMBER: _ClassVar[int]
    HEEL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    STEP_SHAPE_FIELD_NUMBER: _ClassVar[int]
    TENON_FIELD_NUMBER: _ClassVar[int]
    TENON_WIDTH_FIELD_NUMBER: _ClassVar[int]
    TENON_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    strut_inclination: float
    step_depth: float
    heel_depth: float
    step_shape: str
    tenon: bool
    tenon_width: float
    tenon_height: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., strut_inclination: _Optional[float] = ..., step_depth: _Optional[float] = ..., heel_depth: _Optional[float] = ..., step_shape: _Optional[str] = ..., tenon: bool = ..., tenon_width: _Optional[float] = ..., tenon_height: _Optional[float] = ...) -> None: ...

class StepJointNotchData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "strut_inclination", "notch_limited", "notch_width", "step_depth", "heel_depth", "strut_height", "step_shape", "mortise", "mortise_width", "mortise_height")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    STRUT_INCLINATION_FIELD_NUMBER: _ClassVar[int]
    NOTCH_LIMITED_FIELD_NUMBER: _ClassVar[int]
    NOTCH_WIDTH_FIELD_NUMBER: _ClassVar[int]
    STEP_DEPTH_FIELD_NUMBER: _ClassVar[int]
    HEEL_DEPTH_FIELD_NUMBER: _ClassVar[int]
    STRUT_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    STEP_SHAPE_FIELD_NUMBER: _ClassVar[int]
    MORTISE_FIELD_NUMBER: _ClassVar[int]
    MORTISE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    MORTISE_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    strut_inclination: float
    notch_limited: bool
    notch_width: float
    step_depth: float
    heel_depth: float
    strut_height: float
    step_shape: str
    mortise: bool
    mortise_width: float
    mortise_height: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., strut_inclination: _Optional[float] = ..., notch_limited: bool = ..., notch_width: _Optional[float] = ..., step_depth: _Optional[float] = ..., heel_depth: _Optional[float] = ..., strut_height: _Optional[float] = ..., step_shape: _Optional[str] = ..., mortise: bool = ..., mortise_width: _Optional[float] = ..., mortise_height: _Optional[float] = ...) -> None: ...

class DovetailTenonData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "start_depth", "angle", "inclination", "rotation", "length_limited_top", "length_limited_bottom", "length", "width", "height", "cone_angle", "use_flank_angle", "flank_angle", "shape", "shape_radius")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    ROTATION_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_TOP_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_BOTTOM_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    CONE_ANGLE_FIELD_NUMBER: _ClassVar[int]
    USE_FLANK_ANGLE_FIELD_NUMBER: _ClassVar[int]
    FLANK_ANGLE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    inclination: float
    rotation: float
    length_limited_top: bool
    length_limited_bottom: bool
    length: float
    width: float
    height: float
    cone_angle: float
    use_flank_angle: bool
    flank_angle: float
    shape: str
    shape_radius: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., inclination: _Optional[float] = ..., rotation: _Optional[float] = ..., length_limited_top: bool = ..., length_limited_bottom: bool = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., height: _Optional[float] = ..., cone_angle: _Optional[float] = ..., use_flank_angle: bool = ..., flank_angle: _Optional[float] = ..., shape: _Optional[str] = ..., shape_radius: _Optional[float] = ...) -> None: ...

class DovetailMortiseData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "start_x", "start_y", "start_depth", "angle", "slope", "inclination", "limitation_top", "length_limited_bottom", "length", "width", "depth", "cone_angle", "use_flank_angle", "flank_angle", "shape", "shape_radius")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    SLOPE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    LIMITATION_TOP_FIELD_NUMBER: _ClassVar[int]
    LENGTH_LIMITED_BOTTOM_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    CONE_ANGLE_FIELD_NUMBER: _ClassVar[int]
    USE_FLANK_ANGLE_FIELD_NUMBER: _ClassVar[int]
    FLANK_ANGLE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_RADIUS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    slope: float
    inclination: float
    limitation_top: str
    length_limited_bottom: bool
    length: float
    width: float
    depth: float
    cone_angle: float
    use_flank_angle: bool
    flank_angle: float
    shape: str
    shape_radius: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., slope: _Optional[float] = ..., inclination: _Optional[float] = ..., limitation_top: _Optional[str] = ..., length_limited_bottom: bool = ..., length: _Optional[float] = ..., width: _Optional[float] = ..., depth: _Optional[float] = ..., cone_angle: _Optional[float] = ..., use_flank_angle: bool = ..., flank_angle: _Optional[float] = ..., shape: _Optional[str] = ..., shape_radius: _Optional[float] = ...) -> None: ...

class FrenchRidgeLapData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "angle", "ref_position", "drillhole", "drillhole_diam")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    REF_POSITION_FIELD_NUMBER: _ClassVar[int]
    DRILLHOLE_FIELD_NUMBER: _ClassVar[int]
    DRILLHOLE_DIAM_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    angle: float
    ref_position: str
    drillhole: bool
    drillhole_diam: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., angle: _Optional[float] = ..., ref_position: _Optional[str] = ..., drillhole: bool = ..., drillhole_diam: _Optional[float] = ...) -> None: ...

class BirdsMouthData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "start_y", "start_depth", "angle", "inclination_1", "inclination_2", "depth", "width", "width_counter_part_limited", "width_counter_part", "height_counter_part_limited", "height_counter_part", "face_limited_front", "face_limited_back", "lead_angle_parallel", "lead_angle", "lead_inclination_parallel", "lead_inclination", "rafter_nail_hole")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    START_DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_1_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_2_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    WIDTH_COUNTER_PART_LIMITED_FIELD_NUMBER: _ClassVar[int]
    WIDTH_COUNTER_PART_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_COUNTER_PART_LIMITED_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_COUNTER_PART_FIELD_NUMBER: _ClassVar[int]
    FACE_LIMITED_FRONT_FIELD_NUMBER: _ClassVar[int]
    FACE_LIMITED_BACK_FIELD_NUMBER: _ClassVar[int]
    LEAD_ANGLE_PARALLEL_FIELD_NUMBER: _ClassVar[int]
    LEAD_ANGLE_FIELD_NUMBER: _ClassVar[int]
    LEAD_INCLINATION_PARALLEL_FIELD_NUMBER: _ClassVar[int]
    LEAD_INCLINATION_FIELD_NUMBER: _ClassVar[int]
    RAFTER_NAIL_HOLE_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    start_y: float
    start_depth: float
    angle: float
    inclination_1: float
    inclination_2: float
    depth: float
    width: float
    width_counter_part_limited: bool
    width_counter_part: float
    height_counter_part_limited: bool
    height_counter_part: float
    face_limited_front: bool
    face_limited_back: bool
    lead_angle_parallel: bool
    lead_angle: float
    lead_inclination_parallel: bool
    lead_inclination: float
    rafter_nail_hole: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., start_depth: _Optional[float] = ..., angle: _Optional[float] = ..., inclination_1: _Optional[float] = ..., inclination_2: _Optional[float] = ..., depth: _Optional[float] = ..., width: _Optional[float] = ..., width_counter_part_limited: bool = ..., width_counter_part: _Optional[float] = ..., height_counter_part_limited: bool = ..., height_counter_part: _Optional[float] = ..., face_limited_front: bool = ..., face_limited_back: bool = ..., lead_angle_parallel: bool = ..., lead_angle: _Optional[float] = ..., lead_inclination_parallel: bool = ..., lead_inclination: _Optional[float] = ..., rafter_nail_hole: bool = ...) -> None: ...

class LongitudinalCutData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "start_x", "start_y", "inclination", "start_limited", "end_limited", "length", "depth_limited", "depth", "angle_start", "angle_end", "tool_position")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    INCLINATION_FIELD_NUMBER: _ClassVar[int]
    START_LIMITED_FIELD_NUMBER: _ClassVar[int]
    END_LIMITED_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_LIMITED_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    ANGLE_START_FIELD_NUMBER: _ClassVar[int]
    ANGLE_END_FIELD_NUMBER: _ClassVar[int]
    TOOL_POSITION_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    start_x: float
    start_y: float
    inclination: float
    start_limited: bool
    end_limited: bool
    length: float
    depth_limited: bool
    depth: float
    angle_start: float
    angle_end: float
    tool_position: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., inclination: _Optional[float] = ..., start_limited: bool = ..., end_limited: bool = ..., length: _Optional[float] = ..., depth_limited: bool = ..., depth: _Optional[float] = ..., angle_start: _Optional[float] = ..., angle_end: _Optional[float] = ..., tool_position: _Optional[str] = ...) -> None: ...

class SimpleScarfData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "orientation", "start_x", "length", "depth_ref_side", "depth_opp_side", "num_drill_hole", "drill_hole_diam_1", "drill_hole_diam_2")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_REF_SIDE_FIELD_NUMBER: _ClassVar[int]
    DEPTH_OPP_SIDE_FIELD_NUMBER: _ClassVar[int]
    NUM_DRILL_HOLE_FIELD_NUMBER: _ClassVar[int]
    DRILL_HOLE_DIAM_1_FIELD_NUMBER: _ClassVar[int]
    DRILL_HOLE_DIAM_2_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    orientation: str
    start_x: float
    length: float
    depth_ref_side: float
    depth_opp_side: float
    num_drill_hole: int
    drill_hole_diam_1: float
    drill_hole_diam_2: float
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., orientation: _Optional[str] = ..., start_x: _Optional[float] = ..., length: _Optional[float] = ..., depth_ref_side: _Optional[float] = ..., depth_opp_side: _Optional[float] = ..., num_drill_hole: _Optional[int] = ..., drill_hole_diam_1: _Optional[float] = ..., drill_hole_diam_2: _Optional[float] = ...) -> None: ...

class TextData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "start_x", "start_y", "angle", "alignment_vertical", "alignment_horizontal", "alignment_multiline", "stacked_marking", "text_height_auto", "text_height", "text")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    START_X_FIELD_NUMBER: _ClassVar[int]
    START_Y_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    ALIGNMENT_VERTICAL_FIELD_NUMBER: _ClassVar[int]
    ALIGNMENT_HORIZONTAL_FIELD_NUMBER: _ClassVar[int]
    ALIGNMENT_MULTILINE_FIELD_NUMBER: _ClassVar[int]
    STACKED_MARKING_FIELD_NUMBER: _ClassVar[int]
    TEXT_HEIGHT_AUTO_FIELD_NUMBER: _ClassVar[int]
    TEXT_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    start_x: float
    start_y: float
    angle: float
    alignment_vertical: str
    alignment_horizontal: str
    alignment_multiline: str
    stacked_marking: bool
    text_height_auto: bool
    text_height: float
    text: str
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., start_x: _Optional[float] = ..., start_y: _Optional[float] = ..., angle: _Optional[float] = ..., alignment_vertical: _Optional[str] = ..., alignment_horizontal: _Optional[str] = ..., alignment_multiline: _Optional[str] = ..., stacked_marking: bool = ..., text_height_auto: bool = ..., text_height: _Optional[float] = ..., text: _Optional[str] = ...) -> None: ...

class FreeContourData(_message.Message):
    __slots__ = ("guid", "name", "ref_side_index", "priority", "process_id", "contour", "dual_contour", "tool_id", "counter_sink", "tool_position", "depth_bounded")
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REF_SIDE_INDEX_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    CONTOUR_FIELD_NUMBER: _ClassVar[int]
    DUAL_CONTOUR_FIELD_NUMBER: _ClassVar[int]
    TOOL_ID_FIELD_NUMBER: _ClassVar[int]
    COUNTER_SINK_FIELD_NUMBER: _ClassVar[int]
    TOOL_POSITION_FIELD_NUMBER: _ClassVar[int]
    DEPTH_BOUNDED_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    ref_side_index: int
    priority: int
    process_id: int
    contour: ContourData
    dual_contour: DualContourData
    tool_id: int
    counter_sink: bool
    tool_position: str
    depth_bounded: bool
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., ref_side_index: _Optional[int] = ..., priority: _Optional[int] = ..., process_id: _Optional[int] = ..., contour: _Optional[_Union[ContourData, _Mapping]] = ..., dual_contour: _Optional[_Union[DualContourData, _Mapping]] = ..., tool_id: _Optional[int] = ..., counter_sink: bool = ..., tool_position: _Optional[str] = ..., depth_bounded: bool = ...) -> None: ...

class BTLxFromGeometryDefinitionData(_message.Message):
    __slots__ = ("guid", "name", "processing_name", "geometries", "element_guids", "kwargs")
    class KwargsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_pb2.AnyData
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_pb2.AnyData, _Mapping]] = ...) -> None: ...
    GUID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_NAME_FIELD_NUMBER: _ClassVar[int]
    GEOMETRIES_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_GUIDS_FIELD_NUMBER: _ClassVar[int]
    KWARGS_FIELD_NUMBER: _ClassVar[int]
    guid: _common_pb2.GuidRef
    name: str
    processing_name: str
    geometries: _containers.RepeatedCompositeFieldContainer[_message_pb2.AnyData]
    element_guids: _containers.RepeatedCompositeFieldContainer[_common_pb2.GuidRef]
    kwargs: _containers.MessageMap[str, _message_pb2.AnyData]
    def __init__(self, guid: _Optional[_Union[_common_pb2.GuidRef, _Mapping]] = ..., name: _Optional[str] = ..., processing_name: _Optional[str] = ..., geometries: _Optional[_Iterable[_Union[_message_pb2.AnyData, _Mapping]]] = ..., element_guids: _Optional[_Iterable[_Union[_common_pb2.GuidRef, _Mapping]]] = ..., kwargs: _Optional[_Mapping[str, _message_pb2.AnyData]] = ...) -> None: ...

class BTLxProcessingData(_message.Message):
    __slots__ = ("jack_rafter_cut", "double_cut", "drilling", "lap", "mortise", "tenon", "pocket", "slot", "step_joint", "step_joint_notch", "dovetail_tenon", "dovetail_mortise", "french_ridge_lap", "birds_mouth", "longitudinal_cut", "simple_scarf", "text", "free_contour")
    JACK_RAFTER_CUT_FIELD_NUMBER: _ClassVar[int]
    DOUBLE_CUT_FIELD_NUMBER: _ClassVar[int]
    DRILLING_FIELD_NUMBER: _ClassVar[int]
    LAP_FIELD_NUMBER: _ClassVar[int]
    MORTISE_FIELD_NUMBER: _ClassVar[int]
    TENON_FIELD_NUMBER: _ClassVar[int]
    POCKET_FIELD_NUMBER: _ClassVar[int]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    STEP_JOINT_FIELD_NUMBER: _ClassVar[int]
    STEP_JOINT_NOTCH_FIELD_NUMBER: _ClassVar[int]
    DOVETAIL_TENON_FIELD_NUMBER: _ClassVar[int]
    DOVETAIL_MORTISE_FIELD_NUMBER: _ClassVar[int]
    FRENCH_RIDGE_LAP_FIELD_NUMBER: _ClassVar[int]
    BIRDS_MOUTH_FIELD_NUMBER: _ClassVar[int]
    LONGITUDINAL_CUT_FIELD_NUMBER: _ClassVar[int]
    SIMPLE_SCARF_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    FREE_CONTOUR_FIELD_NUMBER: _ClassVar[int]
    jack_rafter_cut: JackRafterCutData
    double_cut: DoubleCutData
    drilling: DrillingData
    lap: LapData
    mortise: MortiseData
    tenon: TenonData
    pocket: PocketData
    slot: SlotData
    step_joint: StepJointData
    step_joint_notch: StepJointNotchData
    dovetail_tenon: DovetailTenonData
    dovetail_mortise: DovetailMortiseData
    french_ridge_lap: FrenchRidgeLapData
    birds_mouth: BirdsMouthData
    longitudinal_cut: LongitudinalCutData
    simple_scarf: SimpleScarfData
    text: TextData
    free_contour: FreeContourData
    def __init__(self, jack_rafter_cut: _Optional[_Union[JackRafterCutData, _Mapping]] = ..., double_cut: _Optional[_Union[DoubleCutData, _Mapping]] = ..., drilling: _Optional[_Union[DrillingData, _Mapping]] = ..., lap: _Optional[_Union[LapData, _Mapping]] = ..., mortise: _Optional[_Union[MortiseData, _Mapping]] = ..., tenon: _Optional[_Union[TenonData, _Mapping]] = ..., pocket: _Optional[_Union[PocketData, _Mapping]] = ..., slot: _Optional[_Union[SlotData, _Mapping]] = ..., step_joint: _Optional[_Union[StepJointData, _Mapping]] = ..., step_joint_notch: _Optional[_Union[StepJointNotchData, _Mapping]] = ..., dovetail_tenon: _Optional[_Union[DovetailTenonData, _Mapping]] = ..., dovetail_mortise: _Optional[_Union[DovetailMortiseData, _Mapping]] = ..., french_ridge_lap: _Optional[_Union[FrenchRidgeLapData, _Mapping]] = ..., birds_mouth: _Optional[_Union[BirdsMouthData, _Mapping]] = ..., longitudinal_cut: _Optional[_Union[LongitudinalCutData, _Mapping]] = ..., simple_scarf: _Optional[_Union[SimpleScarfData, _Mapping]] = ..., text: _Optional[_Union[TextData, _Mapping]] = ..., free_contour: _Optional[_Union[FreeContourData, _Mapping]] = ...) -> None: ...
