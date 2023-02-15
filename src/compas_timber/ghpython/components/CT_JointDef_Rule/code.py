from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.ghpython import CategoryRule


class JointCategoryRule(component):
    # TODO: auto fill with subclasses of Joint
    MAP = {"T-Butt": TButtJoint, "L-Miter": LMiterJoint, "L-Butt": LButtJoint}

    def RunScript(self, JointType, CatA, CatB):
        if JointType and CatA and CatB:
            return CategoryRule(self.MAP[JointType], CatA, CatB)
