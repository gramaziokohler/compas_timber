from compas.geometry import intersection_line_line, intersection_line_plane, distance_point_point, angle_vectors
from compas.geometry import Vector, Point, Plane
from compas.data import Data

# TODO: replace direct references to beam objects


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

    @staticmethod
    def try_add_joint(joint, beams, override=True):
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
        Save guids in each other's attributes
        joint: an instance of a Joint class or its derivative
        beams: list of instances of a Beam class
        """
        #joint.beam_guids = [b.guid for b in beams]
        #for beam in beams: beam.joints.append( {'joint': joint.guid, 'other_beams': [b.guid for b in beams if b=! beam]})

        # NotImplementedError

    @staticmethod
    def __is_joint_already_defined(beams):
        NotImplementedError

    @staticmethod
    def __is_same_joint(joints, beams, joint_uuid, beams_uuid):
        NotImplementedError

    @staticmethod
    def __remove_joint(joints, beams, joint_uuid, beams_uuid):
        NotImplementedError
