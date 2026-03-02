import os
import compas

__version__ = "2.0.0-dev0"

HERE = os.path.dirname(__file__)
HOME = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.abspath(os.path.join(HOME, "data"))


# Check if COMPAS Timber is installed from git
# If that's the case, try to append the current head's hash to __version__
try:
    git_head_file = compas._os.absjoin(HOME, ".git", "HEAD")

    if os.path.exists(git_head_file):
        # git head file contains one line that looks like this:
        # ref: refs/heads/main
        with open(git_head_file, "r") as git_head:
            _, ref_path = git_head.read().strip().split(" ")
            ref_path = ref_path.split("/")

            git_head_refs_file = compas._os.absjoin(HOME, ".git", *ref_path)

        if os.path.exists(git_head_refs_file):
            with open(git_head_refs_file, "r") as git_head_ref:
                git_commit = git_head_ref.read().strip()
                __version__ += "-" + git_commit[:8]
except Exception:
    pass


__all_plugins__ = [
    "compas_timber.rhino",
    "compas_timber.rhino.install",
    "compas_timber.utils.r_tree",
]


__all__ = ["__version__", "DATA", "HOME"]
