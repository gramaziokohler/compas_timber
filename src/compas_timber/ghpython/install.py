from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import glob
import os

import compas.plugins
from compas_ghpython.components import install_userobjects
from compas_ghpython.components import uninstall_userobjects


@compas.plugins.plugin(category="install")
def installable_rhino_packages():
    return ["compas_timber"]


@compas.plugins.plugin(category="install")
def after_rhino_install(installed_packages):
    if "compas_timber" not in installed_packages:
        return []

    installed_objects = install_userobjects(os.path.join(os.path.dirname(__file__), "components", "ghuser"))

    return [
        (
            "compas_timber",
            "Installed {} GH User Objects".format(len(installed_objects)),
            True,
        )
    ]


@compas.plugins.plugin(category="install")
def after_rhino_uninstall(uninstalled_packages):
    if "compas_timber" not in uninstalled_packages:
        return []

    srcdir = os.path.join(os.path.dirname(__file__), "components", "ghuser")
    userobjects = [os.path.basename(ghuser) for ghuser in glob.glob(os.path.join(srcdir, "*.ghuser"))]
    uninstalled_objects = uninstall_userobjects(userobjects)

    uninstall_errors = [uo[0] for uo in uninstalled_objects if not uo[1]]
    error_msg = "" if not uninstall_errors else "and {} failed to uninstall".format(len(uninstall_errors))

    return [
        (
            "compas_timber",
            "Uninstalled {} GH User Objects {}".format(len(uninstalled_objects), error_msg),
            True,
        )
    ]
