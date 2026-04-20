from __future__ import annotations

import uuid
from typing import Optional

from compas.geometry import Frame
from compas.geometry import Transformation

from .part import Part


class Fastener:
    """
    Describes a fastener connecting two or more elements.
    A fastener contains `parts` that are the components of the fastener, and `interactions` that describe how the parts
    interact with each other. Each part can have a parent and/or a child.

    When added to a model, new instances of the fastener are created and added to the model for each `target_frame`
    specified.

    Parameters
    ----------
    frame : Frame, optional
        The frame of the fastener. The default is the world XY frame.
    target_frames : list[Frame], optional
        The target frames where the fastener will be instantiated. The default is None, which means that the fastener will not be instantiated at any target frame. If target
        frames are specified, the fastener will be instantiated at each target frame when added to a model.

    Attributes
    ----------
    frame : Frame
        The frame of the fastener.
    interactions : list[tuple[Part, Part]]
        The interactions between the parts of the fastener. Each interaction is a tuple of (child, parent).
    parts : list[Part]
        The parts that make up the fastener.
    target_frames : list[Frame]
        The target frames where the fastener will be instantiated.
    geometry : list[Geometry]
        The geometry of the fastener, which is the combination of the geometry of its parts.


    """

    def __init__(self, frame: Frame = Frame.worldXY(), target_frames: Optional[list[Frame]] = None):
        self.frame = Frame.worldXY()
        self.interactions = []  # list of interactions tuple (child, parent)
        self.parts = []
        self.target_frames = target_frames
        self.guid = uuid.uuid4()

    @property
    def __data__(self):
        data = {}
        data["frame"] = self.frame.__data__
        data["interactions"] = [(child.guid, parent.guid) for child, parent in self.interactions]
        data["parts"] = [part.__data__ for part in self.parts]
        data["target_frames"] = [frame.__data__ for frame in self.target_frames]
        data["guid"] = str(self.guid)
        return data

    @classmethod
    def from_data(cls, data):
        frame = Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"])
        target_frames = [Frame(frame_data["point"], frame_data["xaxis"], frame_data["yaxis"]) for frame_data in data["target_frames"]]
        parts = [Part.from_data(part_data) for part_data in data["parts"]]

        # create the fastener with the main parts
        fastener = cls(frame, target_frames)

        fastener.parts = parts

        # keep the same guid
        fastener.guid = uuid.UUID(data["guid"])
        return fastener

    @property
    def target_frames(self) -> list[Frame]:
        return self._target_frames

    @target_frames.setter
    def target_frames(self, value: Optional[list[Frame]]):
        if value is None:
            self._target_frames = []
            return
        if not isinstance(value, list):
            raise ValueError("target_frames should be a list of Frames.")
        else:
            self._target_frames = value

    @property
    def geometry(self):
        geometries = []
        for part in self.parts:
            part_geometry = part.geometry
            geometries.append(part_geometry)
        return geometries

    def copy(self) -> Fastener:
        new_fastener = Fastener()
        new_fastener.frame = self.frame.copy()
        new_fastener.parts = [part.copy() for part in self.parts]
        new_fastener.interactions = list(self.interactions)
        new_fastener.target_frames = list(self.target_frames)
        return new_fastener

    def add_part(self, part):
        """
        Add a single part to the fastener. This part does not have interaction with any other parts.

        Parameters
        ----------
        part : Part
            The part to be added to the fastener.

        """
        self.parts.append(part)

    def add_child_part(self, part, parent):
        """
        Add a single part to the fastener.

        Parameters
        ----------

        part : Part
            The part to be added to the fastener.

        parent : list[Part]
            The parent of the part added.
        """
        self.parts.append(part)
        self.interactions.append((part, parent))

    def get_parent(self, part):
        """Return the parent of a specific part."""
        for interaction in self.interactions:
            if interaction[0] == part:
                return interaction[1]
        return None

    def get_children(self, part):
        """Return the children of the specific part."""
        children = []
        for interaction in self.interactions:
            if interaction[1] == part:
                children.append(interaction[0])
        return children

    def get_fastener_instances(self) -> list[Fastener]:
        """
        Get the instances of this fastener at the target frames specified.

        This method is called by `compas_timber.model` and return the fastener instances that are part of the timber model.

        Returns
        -------
        list[Fastener]
            The list of fastener instances at the target frames.
        """

        fastener_instances = []
        for target_frame in self.target_frames:
            # copy and transform the fastener
            fastener_instance = self.copy()
            fastener_instance.frame = target_frame
            fastener_instance.target_frames = None
            transformation = Transformation.from_frame_to_frame(self.frame, target_frame)
            fastener_instance._update_parts_frame(transformation)

            fastener_instances.append(fastener_instance)
        return fastener_instances

    def _update_parts_frame(self, transformation):
        for part in self.parts:
            part.frame = part.frame.transformed(transformation)

    def apply_features(self, elements):
        """
        Apply the processings features generated by the parts to the elements.

        Parameters
        ----------
        elements : list[Element]
            The elements to which the features of the parts will be applied.

        """
        for part in self.parts:
            part.apply_features(elements)
