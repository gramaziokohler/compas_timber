**********************************
Manual installation for developers
**********************************



Use this installation guide if you want to add **COMPAS TIMBER** for development purposes.

    .. note::
        See also details on COMPAS development `here <https://compas.dev/compas/latest/devguide.html#>`__ .


1.  Fork the COMPAS TIMBER `repo <https://github.com/gramaziokohler/compas_timber>`__ and clone the fork.


2.  Navigate to the COMPAS TIMBER repository folder:

    .. code-block:: bash

        cd ..\path-to-compas-timber

3.  Install development dependencies and COMPAS TIMBER:

    .. code-block:: bash

        pip install compas@git+https://github.com/compas-dev/compas@main
        pip install -r requirements-dev.txt


**Rhino & Grasshopper**


4.  Build ghuser components for Grasshopper:

    .. code-block:: bash

        invoke build-ghuser-components


    (Requires IronPython: install from e.g.
    `here <https://github.com/IronLanguages/ironpython2/releases/download/ipy-2.7.12/IronPython-2.7.12.msi>`__,
    and make sure it is added to the environment variables).

5.  Reference COMPAS TIMBER and its dependecies to Rhino and Grasshopper:

    .. code-block:: bash

        python -m compas_rhino.install

    or

    .. code-block:: bash

        python -m compas_rhino.install -v 7.0

    if you need to specify Rhino version (for example 7.0).

