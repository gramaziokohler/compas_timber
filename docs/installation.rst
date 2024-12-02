********************************************************************************
Installation
********************************************************************************

Stable
======

Install with conda
------------------

In an new environment:

.. code-block:: bash

    conda create -n <myenvname> compas_timber -c conda-forge --yes
    conda activate <myenvname>

Install to Rhino 7.0

.. code-block:: bash

    python -m compas_rhino.install -v7.0

Development
===========

To get the latest development version, `fork the repository <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_ and clone the fork

.. code-block:: bash

    git clone https://github.com/<yourgithub_username>/compas_timber.git
    cd compas_timber

Create a new environment if necessary

.. code-block:: bash

    conda create -n <myenvname> python=3.10
    conda activate <myenvname>

Install the package in editable mode with its development dependencies

.. code-block:: bash

    pip install -r requirements-dev.txt

Compile the Grasshopper components

.. code-block:: bash

    invoke build-ghuser-components
    python -m compas_rhino.install -v7.0
