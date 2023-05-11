******************
Quick installation
******************


.. TODO
    update this part so that the user know where to get the files from

**Prerequisites**
Assumes you have:

*   Rhinoceros3D installed
*   ...


**Usage**

| Obtain offline wheels for both COMPAS TIMBER and COMPAS FUTURE, this can be done by donwloading both repositories as a :code:`.zip` file. 
| Place both :code:`.zip` files in a directory together with the script.

(This script relies on the presence of a COMPAS TIMBER and COMPAS FUTURE wheels in the same directory.)



**Windows**

| Copy the :code:`win_install.cmd` script along with a zipped COMPAS TIMBER to the target machine.
| Locate :code:`win_install.cmd` and double click.
| Alternatively, open a :code:`cmd.exe` session, locate the script, and run:

.. code-block:: bash

    win_install.cmd


**Mac**

| Copy :code:`mac_install.cmd` script along with a zipped COMPAS TIMBER to the target machine.
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
5.  Installs COMPAS TIMBER from an offline wheel present in the same directory
6.  Installs COMPAS TIMBER components to the local :code:`Rhino` installation

