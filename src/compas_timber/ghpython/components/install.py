import argparse
import glob
import os

from compas._os import create_symlinks
from compas._os import remove_symlinks
from compas_ghpython import get_grasshopper_userobjects_path
from compas_rhino import _check_rhino_version


def get_version_from_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", choices=["5.0", "6.0", "7.0"], default="7.0")
    args = parser.parse_args()
    return _check_rhino_version(args.version)


def install():
    """Installs the Grasshopper components library."""
    results = []

    try:
        version = get_version_from_args()

        dstdir = get_grasshopper_userobjects_path(version)
        srcdir = os.path.join(os.path.dirname(__file__), "ghuser")
        userobjects = glob.glob(os.path.join(srcdir, "*.ghuser"))

        symlinks_to_remove = []
        symlinks_to_add = []
        for src in userobjects:
            dst = os.path.join(dstdir, os.path.basename(src))
            symlinks_to_remove.append(dst)
            symlinks_to_add.append((src, dst))

        remove_symlinks(symlinks_to_remove)
        create_symlinks(symlinks_to_add)

        results.append(
            (
                "compas_timber",
                "Installed {} GH User Objects".format(len(userobjects)),
                True,
            )
        )
    except PermissionError:
        raise Exception("Please close first all instances of Rhino and then rerun the command")

    return results


def uninstall():
    """Uninstalls the Grasshopper components library."""
    results = []

    try:
        version = get_version_from_args()

        dstdir = get_grasshopper_userobjects_path(version)
        srcdir = os.path.dirname(__file__)
        userobjects = glob.glob(os.path.join(srcdir, "ghuser", "*.ghuser"))

        symlinks = []
        for src in userobjects:
            print(src)
            dst = os.path.join(dstdir, os.path.basename(src))
            symlinks.append(dst)

        remove_symlinks(symlinks)

        results.append(
            (
                "compas_timber",
                "Uninstalled {} GH User Objects".format(len(userobjects)),
                True,
            )
        )
    except PermissionError:
        raise Exception("Please close first all instances of Rhino and then rerun the command")

    return results


if __name__ == "__main__":
    install()
