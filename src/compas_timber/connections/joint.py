from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data
from compas_timber.parts.beam import Beam
from compas.datastructures import Part


# NOTE: some methods assume that for a given set of beams there is only one joint that can connect them.


class Joint(Part):
    """
    parts: beams and other parts of a joint, e.g. a dowel, a steel plate
    assembly: TimberAssembly object to which the parts belong
    """

    def __init__(self, parts=[], assembly=None):
        super(Joint, self).__init__()
        self.assembly = None
        self.frame = None  # will be needed as coordinate system for structural calculations for the forces at the joint
        self.part_keys = []

        for part in parts:
            self.add_part(part, assembly)
        self.add_to_assembly(assembly)

    def add_part(self, part, assembly=None):
        """
        Creates a reference between the joint and a given part in an assembly.
        """
        # if no beams given, do not add joint to assembly (doesn't make sense)
        # if no assembly given, do not add beams nor add joint to assembly

        if not assembly:
            assembly = self.assembly
        if not part or not assembly:
            return None

        # only perform if the part belongs to the same assembly
        assert part.assembly is assembly, "The part does not belong to the same assembly as the given joint's assembly (\n\tpart's assembly: %s\n\tjoint's assembly: %s)" % (
            part.assembly, assembly)
        if part.key not in self.part_keys:
            self.part_keys.append(part.key)

            assert assembly.are_parts_joined_already(self.part_keys) == False, "Cannot add this part: with it, the given set of parts is already joined (%s)" % part

            return part.key

    def add_to_assembly(self, assembly=None):
        # TODO: add check if this instance is already in the assembly
        if not assembly:
            assembly = self.assembly
        if not assembly:
            return None



        key = assembly.add_joint_with_parts(self)  # creates a node for the joint in the graph and connections to its parts
        self.assembly = assembly
        return key

    def remove_from_assembly(self, assembly=None):
        """
        Wrapper for TimberAssembly.remove_joint() so that it's intuitively accessible from Joint
        """

        if not assembly:
            assembly = self.assembly
        if not assembly:
            return
        assembly.remove_joint(self)

    def is_in_assembly(self, assembly=None):
        if not assembly:
            assembly = self.assembly
        if not assembly:
            return False

        return (
            self.key in assembly.joint_keys and
            self is assembly._joints.get(self.key)
        )

    @property
    def parts(self):
        return [self.assembly.find_by_key(key) for key in self.part_keys]

    @property
    def beams(self):
        return [part for part in self.parts if isinstance(part, Beam)]

    # ------------------------------------------------------------------------------------------------
    # WIP alternative way of defining joints without reference to assembly --> saving refs to guids

    def __del__(self):
        """
        Destroys the object
        """
        NotImplementedError

    @staticmethod
    def try_add_joint(joint, beams, override=True):
        """
        Tries to make the connection between the given joint object and the given beams, but checks for conflicts first.
        """
        if Joint.__is_joint_already_defined(beams):
            if Joint.__is_same_joint(joint, beams):
                print('Identical joint already set')
                pass
            else:
                # could be a different joint of the same type, or of a different type
                if override:
                    Joint.__add_joint(joint, beams)
                else:
                    print('Another joint already set.. aborting.')
                    pass
        else:
            Joint.__add_joint(joint, beams)

    @staticmethod
    def __add_joint(joint, beams):
        """
        Makes the connection between the given joint object and the given beams.
        """
        NotImplementedError

    @staticmethod
    def __is_joint_already_defined(beams):
        """
        Checks if there is a joint already defined for the given beams.
        """
        NotImplementedError

    @staticmethod
    def __is_same_joint(joint, beams):
        """
        Checks if the given joint is the same as a joint already defined betwen the given beams.
        """
        NotImplementedError

    @staticmethod
    def __remove_joint(beams):
        """
        Remove any trace of a joint definition between given beams
        (incl. features that were applied to the beams through the joint, or other joint-specific elements such as nails.)
        TODO: if special joining elements present (screws, nails, plates) - should they be deleted?
        Remove joint from assembly if applicable. 
        Delete object.
        """
        NotImplementedError

    def remove_joint(self):
        """
        Remove any trace of this joint from the involved beams (incl. features).
        Remove joint from assembly if applicable. 
        Delete object.
        """
        NotImplementedError

    def __remove_features(self):
        """
        Remove feature definitions that this joint added to the involved beams.
        """
        # TODO: can this be generalized here or should it be in the specific joint types?
        NotImplementedError
