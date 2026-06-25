from compas_model.elements import Element
from compas_pb.conversions import frame_from_pb
from compas_pb.conversions import frame_to_pb
from compas_pb.conversions import mesh_from_pb
from compas_pb.conversions import mesh_to_pb
from compas_pb.core import any_from_pb
from compas_pb.core import any_to_pb
from compas_pb.registry import pb_deserializer
from compas_pb.registry import pb_serializer
from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxProcessing

from compas_timber.proto import elements_pb2
from compas_timber.proto import processing_pb2


@pb_serializer(Beam)
def beam_to_pb(obj: Beam) -> elements_pb2.BeamData:
    proto_data = elements_pb2.BeamData()
    proto_data.guid = str(obj.guid)
    proto_data.name = obj.name
    proto_data.length = obj.length
    proto_data.width = obj.width
    proto_data.height = obj.height
    proto_data.frame.CopyFrom(frame_to_pb(obj.frame))
    return proto_data


@pb_deserializer(elements_pb2.BeamData)
def beam_from_pb(proto_data: elements_pb2.BeamData) -> Beam:
    beam = Beam(
        frame=frame_from_pb(proto_data.frame),
        length=proto_data.length,
        width=proto_data.width,
        height=proto_data.height,
        name=proto_data.name,
    )
    beam._guid = proto_data.guid
    return beam


@pb_serializer(Element)
def element_to_pb(obj: Element) -> elements_pb2.ElementData:
    proto_data = elements_pb2.ElementData()
    proto_data.guid = str(obj.guid)
    proto_data.name = obj.name
    proto_data.frame.CopyFrom(frame_to_pb(obj.frame))
    proto_data.geometry.CopyFrom(mesh_to_pb(obj.geometry))
    return proto_data


@pb_deserializer(elements_pb2.ElementData)
def element_from_pb(proto_data: elements_pb2.ElementData) -> Element:
    element = Element(
        frame=frame_from_pb(proto_data.frame),
        name=proto_data.name,
        geometry=mesh_from_pb(proto_data.geometry),
    )
    element._guid = proto_data.guid
    return element


@pb_serializer(BTLxProcessing)
def processing_to_pb(obj: BTLxProcessing) -> processing_pb2.BTLxProcessingData:
    proto_data = processing_pb2.BTLxProcessingData()
    proto_data.name = obj.PROCESSING_NAME
    proto_data.guid = str(obj.guid)
    for key, value in obj.__data__.items():
        proto_data.params[key].CopyFrom(any_to_pb(value))
    return proto_data


def _fetch_processing_cls_by_name(name: str):
    for cls in BTLxProcessing.__subclasses__():
        if cls.PROCESSING_NAME == name:
            return cls
    raise ValueError(f"Processing class with name '{name}' not found.")


@pb_deserializer(processing_pb2.BTLxProcessingData)
def processing_from_pb(proto_data: processing_pb2.BTLxProcessingData) -> BTLxProcessing:
    cls = _fetch_processing_cls_by_name(proto_data.name)
    data_dict = {key: any_from_pb(value) for key, value in proto_data.params.items()}
    instance = cls.__from_data__(data_dict)
    instance._guid = proto_data.guid
    return instance
