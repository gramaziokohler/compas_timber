def test_ipy_syntax():
    # this is a rather superficial check that these are importable i.e. don't contain any python2.7 syntax errors
    # actual unittests aren't being executed because they occasionally use advanced pytest features which aren't available in ironpython-pytest
    # and it probably makes little sense to add this support due to the emminent deprication of ironpython support
    import compas_timber.connections
    import compas_timber.elements
    import compas_timber.solvers
    import compas_timber.errors
    import compas_timber.fabrication
    import compas_timber.model
    import compas_timber.planning
    import compas_timber.ghpython
    import compas_timber.rhino
