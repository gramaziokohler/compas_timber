from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.ghpython import CategoryRule


class JointCategoryRule(component):
    MAP = {"T-Butt": TButtJoint, "L-Miter": LMiterJoint, "L-Butt": LButtJoint}

    def RunScript(self, joint_type, category_a, category_b):
        if joint_type and category_a and category_b:
            return CategoryRule(self.MAP[joint_type], category_a, category_b)
