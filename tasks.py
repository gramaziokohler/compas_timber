from __future__ import print_function

import os

from compas_invocations2 import build
from compas_invocations2 import docs
from compas_invocations2 import style
from compas_invocations2 import tests

from invoke.collection import Collection


ns = Collection(
    docs.help,
    style.check,
    style.lint,
    style.format,
    docs.docs,
    docs.linkcheck,
    tests.test,
    tests.testdocs,
    tests.testcodeblocks,
    build.prepare_changelog,
    build.clean,
    build.release,
)

ns.configure(
    {
        "base_folder": os.path.dirname(__file__),
    }
)



        for interaction in joint.fasteners_interactions:
            element_a, element_b = interaction
            edge = self.add_interaction(element_a, element_b)
            joint_guids = self._graph.edge_attribute(edge, "joints") or []  # GET
            joint_guids.append(joint_guid)
            self._graph.edge_attribute(edge, "joints", value=joint_guids)
