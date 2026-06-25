import os
import sys

# protoc generates bare `import elements_pb2` style imports; add this directory
# to sys.path so those bare imports resolve correctly when used as a package.
_HERE = os.path.dirname(__file__)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
