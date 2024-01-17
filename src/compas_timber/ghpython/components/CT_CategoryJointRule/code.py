from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.connections import FrenchRidgeLapJoint
from compas_timber.ghpython import CategoryRule


class CategoryJointRule(component):

    def RunScript(self, JointOptions, CatA, CatB):
        if JointOptions and CatA and CatB:
            return CategoryRule(JointOptions.type, CatA, CatB, **JointOptions.kwargs)
