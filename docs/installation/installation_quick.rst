******************
Quick installation
******************


**Prerequisites**
To use the Grasshopper components included with :code:`compas_timber` you need to have [Rhinoceros3D](https://www.rhino3d.com/download/) installed.


**Windows**

| Download the file :code:`win_install.cmd` from [here](https://github.com/gramaziokohler/compas_timber/blob/main/scripts/installers/) or copy its content into a newly created text file (and change the file's extension to :code:`.cmd`)
| Double click :code:`win_install.cmd` to execute.
| Alternatively, open a :code:`cmd.exe` session, locate the file, and run:

.. code-block:: bash

    win_install.cmd


**Mac**

| Download the file :code:`mac_install.cmd` from [here](https://github.com/gramaziokohler/compas_timber/blob/main/scripts/installers/) or copy its content into a newly created text file.
| Open a terminal session, and navigate to the script's location.
| Run the installer using:

.. code-block:: bash

    source mac_install.sh


**What it does in the background**

This batch installer:

1.  Downloads :code:`miniconda` from `here <https://repo.anaconda.com/miniconda/>`__
2.  Installs :code:`miniconda`
3.  Creates a new :code:`conda` virtual environment
4.  Installs COMPAS directly from its main branch on [GitHub](https://github.com/compas-dev/compas)
5.  Installs COMPAS TIMBER from [pip](https://pypi.org/project/compas-timber/)
6.  Installs COMPAS TIMBER components to the local :code:`Rhino` installation
