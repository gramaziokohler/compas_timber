from ghpythonlib.componentbase import executingcomponent as component

from compas_timber.ghpython import CategoryRule


class CategoryJointRule(component):
    def RunScript(self, JointOptions, CatA, CatB):
        if JointOptions and CatA and CatB:
            return CategoryRule(JointOptions.type, CatA, CatB, **JointOptions.kwargs)
