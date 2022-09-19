__author__ = "Aleksandra Anna Apolinarska"
__copyright__ = "Gramazio Kohler Research, ETH Zurich, 2022"
__credits__ = ["Aleksandra Anna Apolinarska"]
__license__ = "MIT"
__version__ = "20.09.2022"

import Rhino
import rhinoscript as rs


def cmd_string_options(
    message="Choose:", oplist=["Option1", "Option2"], default_index=0
):
    """
    message: [str] prompt to the user
    oplist: [str] list of options to display
    default_index : [int] index of the element in the oplist which should be the default option

    returns: [str] the selected or default option, None on fail
    """

    gs = Rhino.Input.Custom.GetOption()
    gs.SetCommandPrompt(message)
    for op in oplist:
        gs.AddOption(op)
    gs.SetDefaultString(oplist[default_index])
    gs.AcceptNothing(True)

    while True:
        result = gs.Get()
        if result == Rhino.Input.GetResult.Cancel:
            return None
        if gs.GotDefault():
            return oplist[default_index]
        else:
            return gs.Option().EnglishName
        break
