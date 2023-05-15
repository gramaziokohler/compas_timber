*******************
Manual installation
*******************



Use this installation guide if you want to add **COMPAS TIMBER** to an existing virutual environment and/or for development purposes.


1.  (Optional) Using `conda <https://anaconda.org/anaconda/conda>`__,
    create a new virtual environment (replace <myenvname> with your desired name), and activate it:

    .. code-block:: bash

       conda create -n <myenvname> python=3.9
       conda activate <myenvname>

2.  Install development dependencies and COMPAS TIMBER:

    **using pip:**

    .. code-block:: bash

        pip install compas@git+https://github.com/compas-dev/compas@main
        pip install compas_timber


    or

    **using conda:**


    .. code-block:: bash

        conda install compas_timber
        pip install compas@git+https://github.com/compas-dev/compas@main

    .. note::

        If you don't have :code:`conda-forge` yet, add it first with:

        .. code-block:: bash

            conda config --env --add channels conda-forge
