from compas.data import Data
from compas.data import json_dump
from compas.data import json_load
from compas.geometry import Frame


class Actor(object):
    """Enum representing the types of actor which could execute an assembly instruction."""

    HUMAN = 0
    ROBOT = 1

    @classmethod
    def get_name(cls, value):
        """Returns the string representation of given actor value.

        For use in logging.

        Parameters
        ----------
        value : int
            One of [Actor.HUMAN, Actor.ROBOT]

        Returns
        -------
        str
            One of ["HUMAN", "ROBOT"]

        """
        try:
            return {v: k for k, v in Actor.__dict__.items() if not k.startswith("_")}[value]
        except KeyError:
            return "UNKNOWN_ACTOR"


class Instruction(Data):
    """Base class for instructions"""

    def __init__(self, id, location):
        super(Instruction, self).__init__()
        self.id = id
        self.location = location

    @property
    def data(self):
        return {
            "id": self.id,
            "location": self.location.data,
        }

    def transform(self, tranformation):
        self.location.transform(tranformation)


class Model3d(Instruction):
    """Instruction which incorporates a 3d model (beam, screw etc.)"""

    def __init__(self, id, location, geometry, element_id, obj_filepath):
        super(Model3d, self).__init__(id, location)
        self.geometry = geometry
        self.element_id = element_id
        self.obj_filepath = obj_filepath

    @property
    def data(self):
        data_dict = {
            "geometry": self.geometry,
            "element_id": self.element_id,
            "obj_filepath": self.obj_filepath,
        }
        data_dict.update(super(Model3d, self).data)
        return data_dict

    def transform(self, tranformation):
        super(Model3d, self).transform(tranformation)
        self.geometry.transform(tranformation)


class Text3d(Instruction):
    """Text overlay"""

    def __init__(self, id, location, text, size):
        super(Text3d, self).__init__(id, location)
        self.text = text
        self.size = size

    @property
    def data(self):
        data_dict = {
            "text": self.text,
            "size": self.size,
        }
        data_dict.update(super(Text3d, self).data)
        return data_dict


class LinearDimension(Instruction):
    """3d linear dimension"""

    def __init__(self, id, location, start, end, char_size, offset):
        super(LinearDimension, self).__init__(id, location)
        self.start = start
        self.end = end
        self.char_size = char_size
        self.offset = offset

    @property
    def data(self):
        data_dict = {
            "start": self.start,
            "end": self.end,
            "char_size": self.char_size,
            "offset": self.offset,
        }
        data_dict.update(super(LinearDimension, self).data)
        return data_dict

    def transform(self, tranformation):
        super(LinearDimension, self).transform(tranformation)
        self.start.transform(tranformation)
        self.end.transform(tranformation)


class Step(Data):
    """Container for building instructions which assemble a single element

    Attributes
    ----------
    location : :class:`compas.geometry.Frame`  # TODO: replace with Transformation?
        Location of the step.
    obj_filepath : str
        Path to the 3d model of the element(s) which belong to this step.
    instructions : list(:class:`Instruction`)
        List of instructions which make up the step.
    element_ids : list(int)
        List of cad element ids which are associated with the step.

    """

    def __init__(
        self,
        element_ids,
        location=None,
        obj_filepath=None,
        step_id=None,
        instructions=None,
        is_built=False,
        actor=None,
    ):
        super(Step, self).__init__()
        self.element_ids = element_ids or []
        self.location = location or Frame.worldXY()
        self.obj_filepath = obj_filepath
        self.step_id = step_id
        self.instructions = instructions or []
        self.is_built = is_built
        self._actor = actor

    @property
    def actor(self):
        return self._actor

    @actor.setter
    def actor(self, value):
        if isinstance(value, str):
            self._actor = getattr(Actor, value, "UNKNOWN_ACTOR")
        else:
            self._actor = value

    @property
    def data(self):
        return {
            "location": self.location.data,
            "obj_filepath": self.obj_filepath,
            "step_id": self.step_id,
            "element_ids": self.element_ids,
            "instructions": self.instructions,
            "is_built": self.is_built,
            "actor": Actor.get_name(self.actor),
        }

    def transform(self, transformation):
        self.location.transform(transformation)


class BuildingPlanParser(object):
    """Provides class methods to parse and serialize building plans from and to json files.

    This implementation does it the COMPAS way.
    Implemet your own `parse()` and `serialize()` methods if you want to use a different format.

    """

    @classmethod
    def parse(cls, filepath):
        """Parses building plan from json file.

        Parameters
        ----------
        filepath : str
            Path to json file

        Returns
        -------
        :class:`BuildingPlan`

        """
        return json_load(filepath)

    @classmethod
    def serialize(cls, building_plan, filepath):
        """Writes building plan to json file.

        Parameters
        ----------
        building_plan : :class:`BuildingPlan`
            Building plan to be serialized.
        filepath : str
            Path to json file.

        """
        json_dump(building_plan, filepath)


class BuildingPlan(Data):
    """Container for building steps, each steps is a collection of instructions which can be visualized"""

    def __init__(self, steps=None):
        super(BuildingPlan, self).__init__()
        self.steps = steps or []

    def __repr__(self):
        return "BuildingPlan with {} steps".format(len(self.steps))

    def __iter__(self):
        return iter(self.steps)

    def __len__(self):
        return len(self.steps)

    @property
    def data(self):
        return {"steps": self.steps}

    def add_step(self, step):
        self.steps.append(step)


class SimpleSequenceGenerator(object):
    """Generates a simple sequence of steps, one step per element.
    Order of steps is the same as order of elements in assembly.

    Parameters
    ----------
    assembly : :class:`compas_timber.assembly.TimberAssembly`
        Assembly to be sequenced.

    Attributes
    ----------
    result : :class:`BuildingPlan`
        Resulting building plan.

    """

    def __init__(self, assembly):
        self.assembly = assembly

    @property
    def result(self):
        plan = BuildingPlan()
        for beam in self.assembly.beams:
            # TODO: Mesh.from_shape(beam.blank).to_obj(filepath) and use that as obj_filepath
            plan.add_step(Step(element_ids=[beam.key], actor=Actor.HUMAN))
        return plan
