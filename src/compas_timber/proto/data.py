"""Protobuf serializers for compas_timber.

Registered with compas_pb through the ``compas_pb.plugins`` entry point, so
``compas_pb.pb_dump_bts`` / ``pb_load_bts`` can round-trip a whole TimberModel.

The mapping between a class and its proto message is driven by the message
descriptor itself: proto field names match the keys of the class' ``__data__``,
so the codec below reads the descriptor to decide how to convert each field.
That keeps the ``.proto`` files the single source of truth -- adding a field to
a message is enough, as long as ``__data__`` uses the same key.

``guid`` and ``name`` are carried by the compas serialization envelope rather
than by ``__data__``, so every message reserves fields 1 and 2 for them.
"""

from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_pb.conversions import frame_from_pb
from compas_pb.conversions import frame_to_pb
from compas_pb.conversions import line_from_pb
from compas_pb.conversions import line_to_pb
from compas_pb.conversions import point_from_pb
from compas_pb.conversions import point_to_pb
from compas_pb.conversions import polyline_from_pb
from compas_pb.conversions import polyline_to_pb
from compas_pb.conversions import transformation_from_pb
from compas_pb.conversions import transformation_to_pb

# compas_pb's public any_to_pb/any_from_pb only cover Data objects and
# primitives; these two also handle plain dicts and lists, which several
# __data__ implementations (notably Model.tree / Model.graph) contain.
from compas_pb.core import _deserialize_any as any_from_pb
from compas_pb.core import _serializer_any as any_to_pb
from compas_pb.registry import SerializerRegistry
from compas_pb.registry import pb_deserializer
from compas_pb.registry import pb_serializer
from google.protobuf.descriptor import FieldDescriptor

# ---------------------------------------------------------------------------
# geometry converters, keyed by proto message name
# ---------------------------------------------------------------------------

_GEOMETRY = {
    "compas_pb.data.PointData": (Point, point_to_pb, point_from_pb),
    "compas_pb.data.FrameData": (Frame, frame_to_pb, frame_from_pb),
    "compas_pb.data.PolylineData": (Polyline, polyline_to_pb, polyline_from_pb),
    "compas_pb.data.LineData": (Line, line_to_pb, line_from_pb),
    "compas_pb.data.TransformationData": (Transformation, transformation_to_pb, transformation_from_pb),
}
_ANY = "compas_pb.data.AnyData"


def _nested_to_pb(obj):
    """Serialize a nested compas object using whatever serializer is registered for it."""
    fn = SerializerRegistry.get_serializer(obj)
    if fn is None:
        raise TypeError("no protobuf serializer registered for {!r}".format(type(obj).__name__))
    return fn(obj)


def _nested_from_pb(msg):
    fn = SerializerRegistry.get_deserializer(msg.DESCRIPTOR.full_name)
    if fn is None:
        raise TypeError("no protobuf deserializer registered for {}".format(msg.DESCRIPTOR.full_name))
    return fn(msg)


def _is_map(field):
    return field.type == FieldDescriptor.TYPE_MESSAGE and field.message_type.GetOptions().map_entry


# ---------------------------------------------------------------------------
# generic field codec
# ---------------------------------------------------------------------------


def _field_to_pb(msg, field, value):
    name = field.name
    if value is None:
        return
    if _is_map(field):
        vfield = field.message_type.fields_by_name["value"]
        target = getattr(msg, name)
        for k, v in dict(value).items():
            if vfield.type == FieldDescriptor.TYPE_MESSAGE and vfield.message_type.full_name == _ANY:
                target[k].CopyFrom(any_to_pb(v))
            else:
                target[k] = v
        return

    repeated = field.is_repeated
    if repeated and isinstance(value, dict):
        # compas_model keeps elements / materials / joints in guid-keyed dicts
        value = list(value.values())
    if field.type != FieldDescriptor.TYPE_MESSAGE:
        if repeated:
            getattr(msg, name).extend(list(value))
        else:
            setattr(msg, name, value)
        return

    tname = field.message_type.full_name
    if repeated:
        target = getattr(msg, name)
        for item in value:
            if tname == _ANY:
                target.add().CopyFrom(any_to_pb(item))
            elif tname in _GEOMETRY:
                target.add().CopyFrom(_GEOMETRY[tname][1](item))
            else:
                target.add().CopyFrom(_wrap(field.message_type, item))
        return

    if tname == _ANY:
        getattr(msg, name).CopyFrom(any_to_pb(value))
    elif tname in _GEOMETRY:
        cls, to_pb_fn, _ = _GEOMETRY[tname]
        # a few __data__ implementations store `obj.__data__` rather than obj
        if isinstance(value, dict):
            value = cls.__from_data__(value)
        getattr(msg, name).CopyFrom(to_pb_fn(value))
    else:
        getattr(msg, name).CopyFrom(_wrap(field.message_type, value))


def _field_from_pb(msg, field):
    name = field.name
    if _is_map(field):
        vfield = field.message_type.fields_by_name["value"]
        raw = getattr(msg, name)
        if vfield.type == FieldDescriptor.TYPE_MESSAGE and vfield.message_type.full_name == _ANY:
            return {k: any_from_pb(v) for k, v in raw.items()}
        return dict(raw)

    repeated = field.is_repeated
    if field.type != FieldDescriptor.TYPE_MESSAGE:
        if repeated:
            return list(getattr(msg, name))
        return getattr(msg, name) if (not field.has_presence or msg.HasField(name)) else None

    tname = field.message_type.full_name
    if repeated:
        items = getattr(msg, name)
        if tname == _ANY:
            return [any_from_pb(i) for i in items]
        if tname in _GEOMETRY:
            return [_GEOMETRY[tname][2](i) for i in items]
        return [_unwrap(i) for i in items]

    if not msg.HasField(name):
        return None
    sub = getattr(msg, name)
    if tname == _ANY:
        return any_from_pb(sub)
    if tname in _GEOMETRY:
        return _GEOMETRY[tname][2](sub)
    return _unwrap(sub)


# ---------------------------------------------------------------------------
# oneof wrappers
# ---------------------------------------------------------------------------

_WRAPPERS = {}  # wrapper message full_name -> wrapper message class


def _wrap(descriptor, obj):
    """Put ``obj`` into a wrapper message if the target field is a oneof wrapper."""
    wrapper_cls = _WRAPPERS.get(descriptor.full_name)
    inner = _nested_to_pb(obj)
    if wrapper_cls is None:
        return inner
    wrapper = wrapper_cls()
    for f in descriptor.fields:
        if f.message_type is not None and f.message_type.full_name == inner.DESCRIPTOR.full_name:
            getattr(wrapper, f.name).CopyFrom(inner)
            return wrapper
    raise TypeError("{} cannot hold a {}".format(descriptor.full_name, inner.DESCRIPTOR.full_name))


def _unwrap(msg):
    if msg.DESCRIPTOR.full_name in _WRAPPERS:
        which = msg.WhichOneof(msg.DESCRIPTOR.oneofs[0].name)
        if which is None:
            return None
        return _nested_from_pb(getattr(msg, which))
    return _nested_from_pb(msg)


def register_wrapper(msg_cls):
    """Register a message whose only content is a oneof over concrete messages."""
    _WRAPPERS[msg_cls.DESCRIPTOR.full_name] = msg_cls
    return msg_cls


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------


def register(cls, msg_cls, aliases=None, from_data=None, catchall="attributes", name_in_data=False, raw_dict_fields=(), guid_dict_fields=()):
    """Register a serializer/deserializer pair for ``cls`` <-> ``msg_cls``.

    Parameters
    ----------
    cls : type
        The compas class.
    msg_cls : type
        The generated protobuf message class.
    aliases : dict, optional
        Maps a proto field name to the ``__data__`` key it stands for, for the
        few places where the two differ.
    from_data : callable, optional
        Overrides ``cls.__from_data__`` when rebuilding the object.
    """
    aliases = aliases or {}
    fields = [f for f in msg_cls.DESCRIPTOR.fields if f.name not in ("guid", "name")]
    catch = catchall if catchall and any(f.name == catchall for f in fields) else None
    known = {aliases.get(f.name, f.name) for f in fields}
    known.discard(catch)
    if name_in_data:
        # a genuine __data__ key, handled via the envelope rather than the
        # catch-all; otherwise `name` is just another kwarg in `attributes`.
        known.add("name")

    def to_pb(obj, _msg_cls=msg_cls, _fields=fields, _aliases=aliases, _catch=catch, _known=known):
        msg = _msg_cls()
        msg.guid = str(obj.guid)
        # `obj.name` falls back to the class name when unset; `_name` is the
        # raw value, so an unnamed object stays unnamed across a round-trip.
        if getattr(obj, "_name", None) is not None:
            msg.name = obj._name
        data = obj.__data__
        for f in _fields:
            if f.name == _catch:
                # classes that do `data.update(self.attributes)` merge unknown
                # keys straight into __data__; everything unaccounted for is one
                # of those and belongs in the catch-all map.
                _field_to_pb(msg, f, {k: v for k, v in data.items() if k not in _known})
            else:
                _field_to_pb(msg, f, data.get(_aliases.get(f.name, f.name)))
        return msg

    def from_pb(
        msg,
        _cls=cls,
        _fields=fields,
        _aliases=aliases,
        _from_data=from_data,
        _catch=catch,
        _name_in_data=name_in_data,
        _raw_dicts=raw_dict_fields,
        _guid_dicts=guid_dict_fields,
    ):
        data = {}
        extras = {}
        for f in _fields:
            value = _field_from_pb(msg, f)
            if f.name in _raw_dicts and value is not None:
                value = value.__data__
            if f.name in _guid_dicts and value is not None:
                value = {str(item.guid): item for item in value}
            if f.name == _catch:
                extras = value or {}
            else:
                data[_aliases.get(f.name, f.name)] = value
        data.update(extras)
        if _name_in_data:
            # pass the name explicitly, None included, so a constructor default
            # cannot substitute a name onto an object that had none
            data["name"] = msg.name if msg.HasField("name") else None
        builder = _from_data or _cls.__from_data__
        obj = builder(data)
        obj._guid = msg.guid
        if msg.HasField("name"):
            obj.name = msg.name
        return obj

    pb_serializer(cls)(to_pb)
    pb_deserializer(msg_cls)(from_pb)
    return to_pb, from_pb


# ---------------------------------------------------------------------------
# fabrication
# ---------------------------------------------------------------------------

from compas_timber import fabrication as _fab  # noqa: E402
from compas_timber.proto import connections_pb2  # noqa: E402
from compas_timber.proto import elements_pb2  # noqa: E402
from compas_timber.proto import fabrication_pb2  # noqa: E402
from compas_timber.proto import model_pb2  # noqa: E402
from compas_timber.proto import panel_features_pb2  # noqa: E402
from compas_timber.proto import planning_pb2  # noqa: E402
from compas_timber.proto import structural_pb2  # noqa: E402

register(_fab.Contour, fabrication_pb2.ContourData)
register(_fab.DualContour, fabrication_pb2.DualContourData)

# every BTLxProcessing whose fields are plain scalars (plus machining_limits)
_PROCESSINGS = [
    "JackRafterCut", "DoubleCut", "Drilling", "Lap", "Mortise", "Tenon", "Pocket", "Slot",
    "StepJoint", "StepJointNotch", "DovetailTenon", "DovetailMortise", "FrenchRidgeLap",
    "BirdsMouth", "LongitudinalCut", "SimpleScarf", "Text",
]
for _n in _PROCESSINGS:
    register(getattr(_fab, _n), getattr(fabrication_pb2, _n + "Data"))


# FreeContour holds either a Contour or a DualContour under one __data__ key.
def _freecontour_to_pb(obj):
    msg = fabrication_pb2.FreeContourData()
    msg.guid = str(obj.guid)
    if getattr(obj, "_name", None) is not None:
        msg.name = obj._name
    data = obj.__data__
    for key in ("ref_side_index", "priority", "process_id", "tool_id", "counter_sink", "tool_position", "depth_bounded"):
        if data.get(key) is not None:
            setattr(msg, key, data[key])
    param = data.get("contour_param_object")
    if isinstance(param, _fab.DualContour):
        msg.dual_contour.CopyFrom(_nested_to_pb(param))
    elif param is not None:
        msg.contour.CopyFrom(_nested_to_pb(param))
    return msg


def _freecontour_from_pb(msg):
    data = {k: (getattr(msg, k) if msg.HasField(k) else None)
            for k in ("ref_side_index", "priority", "process_id", "tool_id", "counter_sink", "tool_position", "depth_bounded")}
    which = msg.WhichOneof("contour_param_object")
    data["contour_param_object"] = _nested_from_pb(getattr(msg, which)) if which else None
    obj = _fab.FreeContour.__from_data__(data)
    obj._guid = msg.guid
    if msg.HasField("name"):
        obj.name = msg.name
    return obj


pb_serializer(_fab.FreeContour)(_freecontour_to_pb)
pb_deserializer(fabrication_pb2.FreeContourData)(_freecontour_from_pb)


def _btlxdef_to_pb(obj):
    msg = fabrication_pb2.BTLxFromGeometryDefinitionData()
    msg.guid = str(obj.guid)
    if getattr(obj, "_name", None) is not None:
        msg.name = obj._name
    msg.processing_name = obj.processing.__name__
    for g in obj.geometries:
        msg.geometries.add().CopyFrom(any_to_pb(g))
    msg.element_guids.extend([str(e.guid) for e in obj.elements])
    for k, v in (obj.kwargs or {}).items():
        msg.kwargs[k].CopyFrom(any_to_pb(v))
    return msg


def _btlxdef_from_pb(msg):
    obj = _fab.BTLxFromGeometryDefinition(
        getattr(_fab, msg.processing_name),
        [any_from_pb(g) for g in msg.geometries],
        [],
        **{k: any_from_pb(v) for k, v in msg.kwargs.items()}
    )
    obj._guid = msg.guid
    if msg.HasField("name"):
        obj.name = msg.name
    return obj


pb_serializer(_fab.BTLxFromGeometryDefinition)(_btlxdef_to_pb)
pb_deserializer(fabrication_pb2.BTLxFromGeometryDefinitionData)(_btlxdef_from_pb)

register_wrapper(fabrication_pb2.BTLxProcessingData)

# ---------------------------------------------------------------------------
# panel features
# ---------------------------------------------------------------------------

from compas_timber import panel_features as _pf  # noqa: E402

register(_pf.Opening, panel_features_pb2.OpeningData, name_in_data=True)
register(_pf.PanelConnectionInterface, panel_features_pb2.PanelConnectionInterfaceData, name_in_data=True)
register_wrapper(panel_features_pb2.PanelFeatureData)

# ---------------------------------------------------------------------------
# elements
# ---------------------------------------------------------------------------

from compas_timber import elements as _el  # noqa: E402

register(_el.PlateGeometry, elements_pb2.PlateGeometryData)
register(_el.LayerDefinition, elements_pb2.LayerDefinitionData, name_in_data=True)
register(_el.LayerStructure, elements_pb2.LayerStructureData)
register(_el.Beam, elements_pb2.BeamData)
register(_el.Plate, elements_pb2.PlateData)
register(_el.Panel, elements_pb2.PanelData)
register(_el.FastenerTimberInterface, elements_pb2.FastenerTimberInterfaceData, aliases={"element_guid": "element"})
register(_el.Fastener, elements_pb2.FastenerData)
register(_el.BallNodeFastener, elements_pb2.BallNodeFastenerData)
register(_el.PlateFastener, elements_pb2.PlateFastenerData)


# Layer.layer_path is a tuple-or-None, wrapped so the two stay distinct.
def _layer_to_pb(obj):
    msg = elements_pb2.LayerData()
    msg.guid = str(obj.guid)
    if getattr(obj, "_name", None) is not None:
        msg.name = obj._name
    data = obj.__data__
    msg.plate_geometry.CopyFrom(_nested_to_pb(data["plate_geometry"]))
    if data.get("start_offset") is not None:
        msg.start_offset = data["start_offset"]
    if data.get("layer_path") is not None:
        msg.layer_path.indices.extend(data["layer_path"])
    return msg


def _layer_from_pb(msg):
    data = {
        "plate_geometry": _nested_from_pb(msg.plate_geometry),
        "start_offset": msg.start_offset if msg.HasField("start_offset") else None,
        "layer_path": list(msg.layer_path.indices) if msg.HasField("layer_path") else None,
        "name": msg.name if msg.HasField("name") else None,
    }
    obj = _el.Layer.__from_data__(data)
    obj._guid = msg.guid
    return obj


pb_serializer(_el.Layer)(_layer_to_pb)
pb_deserializer(elements_pb2.LayerData)(_layer_from_pb)

# A bare compas_model Element. Registered last so the MRO lookup in
# SerializerRegistry.get_serializer only reaches it for elements that are not
# one of the timber types above.
from compas_model.elements import Element as _GenericElement  # noqa: E402

register(_GenericElement, elements_pb2.GenericElementData, name_in_data=True)

register_wrapper(elements_pb2.ElementData)

# ---------------------------------------------------------------------------
# connections
# ---------------------------------------------------------------------------

import inspect as _inspect  # noqa: E402

from compas_timber import connections as _cn  # noqa: E402

register(_cn.CutPlaneSpec, connections_pb2.CutPlaneSpecData)
register(_cn.MiterPlaneSpec, connections_pb2.MiterPlaneSpecData)
register(_cn.JointCandidate, connections_pb2.JointCandidateData, catchall="extra_kwargs", name_in_data=True)
from compas_timber.connections.solver import BeamSolverResult as _BeamSolverResult  # noqa: E402
from compas_timber.connections.solver import PlateSolverResult as _PlateSolverResult  # noqa: E402

register(_BeamSolverResult, connections_pb2.BeamSolverResultData,
         aliases={"beam_a_guid": "beam_a", "beam_b_guid": "beam_b"})
register(_PlateSolverResult, connections_pb2.PlateSolverResultData,
         aliases={"plate_a_guid": "plate_a", "plate_b_guid": "plate_b"})

for _name in dir(_cn):
    _obj = getattr(_cn, _name)
    if (_inspect.isclass(_obj) and issubclass(_obj, _cn.Joint) and _obj is not _cn.Joint
            and not getattr(_obj, "__abstractmethods__", frozenset())):
        _msg = getattr(connections_pb2, _name + "Data", None)
        if _msg is not None:
            register(_obj, _msg, name_in_data=True)

register_wrapper(connections_pb2.JointData)

# ---------------------------------------------------------------------------
# structural
# ---------------------------------------------------------------------------

from compas_timber.structural import StructuralSegment  # noqa: E402


def _segment_to_pb(obj):
    msg = structural_pb2.StructuralSegmentData()
    msg.guid = str(obj.guid)
    if getattr(obj, "_name", None) is not None:
        msg.name = obj._name
    data = obj.__data__
    msg.line.CopyFrom(line_to_pb(data["line"]))
    msg.frame.CopyFrom(frame_to_pb(data["frame"]))
    if data.get("cross_section") is not None:
        msg.cross_section.extend(list(data["cross_section"]))
        msg.cross_section_set = True
    for k, v in data.items():
        if k not in ("line", "frame", "cross_section", "name"):
            msg.attributes[k].CopyFrom(any_to_pb(v))
    return msg


def _segment_from_pb(msg):
    data = {
        "line": line_from_pb(msg.line),
        "frame": frame_from_pb(msg.frame),
        "cross_section": tuple(msg.cross_section) if msg.cross_section_set else None,
    }
    data.update({k: any_from_pb(v) for k, v in msg.attributes.items()})
    obj = StructuralSegment.__from_data__(data)
    obj._guid = msg.guid
    if msg.HasField("name"):
        obj.name = msg.name
    return obj


pb_serializer(StructuralSegment)(_segment_to_pb)
pb_deserializer(structural_pb2.StructuralSegmentData)(_segment_from_pb)

# ---------------------------------------------------------------------------
# planning
# ---------------------------------------------------------------------------

from compas_timber import planning as _pl  # noqa: E402

# Instruction subclasses store `location.__data__` rather than the Frame itself.
register(_pl.Model3d, planning_pb2.Model3dData, raw_dict_fields=("location",))
register(_pl.Text3d, planning_pb2.Text3dData, raw_dict_fields=("location",))
register(_pl.LinearDimension, planning_pb2.LinearDimensionData, raw_dict_fields=("location",))
register_wrapper(planning_pb2.InstructionData)

register(_pl.Step, planning_pb2.StepData, raw_dict_fields=("location",))
register(_pl.BuildingPlan, planning_pb2.BuildingPlanData)

register(_pl.NestedElementData, planning_pb2.NestedElementDataData)
register(_pl.BeamStock, planning_pb2.BeamStockData)
register(_pl.PlateStock, planning_pb2.PlateStockData)
register_wrapper(planning_pb2.StockData)
register(_pl.NestingResult, planning_pb2.NestingResultData)


def _container_to_pb(obj):
    msg = planning_pb2.BuildingPlanModelContainerData()
    msg.plan.CopyFrom(_nested_to_pb(obj.plan))
    for guid, element in obj.elements.items():
        msg.elements[guid].CopyFrom(_wrap(elements_pb2.ElementData.DESCRIPTOR, element))
    for guid, geometry in obj.geometries.items():
        if isinstance(geometry, str):
            msg.geometries[guid].firebase_filename = geometry
        else:
            msg.geometries[guid].geometry.CopyFrom(any_to_pb(geometry))
    return msg


def _container_from_pb(msg):
    elements = {guid: _unwrap(e) for guid, e in msg.elements.items()}
    geometries = {}
    for guid, geo in msg.geometries.items():
        which = geo.WhichOneof("kind")
        geometries[guid] = geo.firebase_filename if which == "firebase_filename" else any_from_pb(geo.geometry)
    return _pl.BuildingPlanModelContainer(_nested_from_pb(msg.plan), elements, geometries)


pb_serializer(_pl.BuildingPlanModelContainer)(_container_to_pb)
pb_deserializer(planning_pb2.BuildingPlanModelContainerData)(_container_from_pb)

# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------

from compas_timber.model import TimberModel  # noqa: E402

register(TimberModel, model_pb2.TimberModelData, guid_dict_fields=("elements", "materials", "joints"))
