from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data


# NOTE: some methods assume that for a given set of beams there is only one joint that can connect them.


class Joint(Data):
    def __init__(self, assembly=None, beams = []):
        super(Joint, self).__init__()
        self.assembly = assembly
        self.beam_keys = []
        self.beam_guids = []
        self.joint_type_name = ''
        self.frame = None  # will be needed as coordinate system for structural calculations for the forces at the joint
        
        if beams: 
            self.beam_keys = [b.key for b in beams]
            self.beam_guids = [b.guid for b in beams]  # WIP

            assembly.add_joint(self)
            assembly.connect(self, beams)

    @property
    def beams(self):
        return [self.assembly.find_by_key(key) for key in self.beam_keys]

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

    @staticmethod #
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
        #TODO: can this be generalized here or should it be in the specific joint types?
        NotImplementedError