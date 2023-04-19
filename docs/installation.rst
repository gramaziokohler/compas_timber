********************************************************************************
Installation
********************************************************************************



Quick installation
==================

.. TODO
    update this part so that the user know where to get the files from

**Usage**

| Obtain offline wheels for both :code:`compas_timber` and :code:`compas_future`, this can be done by donwloading both repositories as a :code:`.zip` file. 
| Place both :code:`.zip` files in a directory together with the script.

(This script relies on the presence of a :code:`compas_timber` and :code:`compas_future` wheels in the same directory.)

**Windows**

| Copy the :code:`win_install.cmd` script along with a zipped :code:`compas_timber` to the target machine.
| Locate :code:`win_install.cmd` and double click.
| Alternatively, open a :code:`cmd.exe` session, locate the script, and run:

.. code-block:: bash

    win_install.cmd


**Mac**

| Copy :code:`mac_install.cmd` script along with a zipped :code:`compas_timber` to the target machine.
| Open a terminal session, and navigate to the script's location.
| Run the installer using:

.. code-block:: bash

    source mac_install.sh


**What it does in the background**

This batch installer:

1.  Downloads :code:`miniconda` from `here <https://repo.anaconda.com/miniconda/>`__
2.  Installs :code:`miniconda`
3.  Creates a new :code:`conda` virtual environment with COMPAS and required dependencies
4.  Installs :code:`compas_future` from an offline wheel present in the same directory
5.  Installs :code:`compas_timber` from an offline wheel present in the same directory
6.  Installs :code:`compas_timber` components to the local :code:`Rhino` installation




Manual installation
===================

Use this installation guide if you want to add **compas_timber** to an existing virutual environment and/or for development purposes.

1.  Download the **compas_timber** `repo <https://github.com/gramaziokohler/compas_timber>`__ and unpack, or clone.

2.  (Optional) Using `conda <https://anaconda.org/anaconda/conda>`__, 
    create a new virtual environment (replace :code:`<myenvname>` with your desired name), and activate it: 

    .. code-block:: bash 

       conda create -n <myenvname> python=3.9
       conda activate <myenvname>

4.  Navigate to the **compas_timber** folder:

    .. code-block:: bash

        cd ..\path-to-folder

5.  Install development dependencies and **compas_timber**:

    .. code-block:: bash

        pip install -r requirements-dev.txt

**Rhino & Grasshopper**


7.  `Build <https://github.com/compas-dev/compas/blob/8e21328efc0c192bd9f5f25698156778ca7a7a58/docs/devguide.rst#grasshopper-components>`__ 
    ghuser components for Grasshopper:

    .. code-block:: bash

        invoke build-ghuser-components


    (Requires IronPython: install from e.g. 
    `here <https://github.com/IronLanguages/ironpython2/releases/download/ipy-2.7.12/IronPython-2.7.12.msi>`__, 
    and make sure it is added to the environment variables).

8.  Reference **compas_timber** and its dependecies to Rhino and Grasshopper:

    .. code-block:: bash

        python -m compas_rhino.install 

    or

    .. code-block:: bash 

        python -m compas_rhino.install -v 7.0 
    
    if you need to specify Rhino version (for example 7.0).