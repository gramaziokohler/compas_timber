import Rhino
import scriptcontext as sc

sc.doc = Rhino.RhinoDoc.ActiveDoc
keys = sc.sticky.keys()
keys.sort()

if keys == []:
    print("The sticky is empty.")
else:
    g0 = Rhino.Input.Custom.GetOption()
    g0.SetCommandPrompt("Select option:..")
    for func in ["Show", "Clear", "ShowAll", "ClearAll"]:
        g0.AddOption(func)
    # g0.SetDefaultString('Show')
    # g0.AcceptNothing(True)

    while True:
        result0 = g0.Get()
        if result0 == Rhino.Input.GetResult.Cancel:
            pass
        else:
            result0 = g0.Option().EnglishName
        break

    if result0 == "Show":
        g1 = Rhino.Input.Custom.GetOption()
        g1.SetCommandPrompt("Select sticky key:..")
        for k in keys:
            g1.AddOption(k)
        # g1.SetDefaultString(keys[0])
        # g1.AcceptNothing(True)
        while True:
            result = g1.Get()
            if result == Rhino.Input.GetResult.Cancel:
                pass
            else:
                selected_key = g1.Option().EnglishName
                print("[%s]: %s" % (selected_key, sc.sticky[selected_key]))
            break

    elif result0 == "Clear":
        g2 = Rhino.Input.Custom.GetOption()
        g2.SetCommandPrompt("Select sticky key:..")
        for k in keys:
            g2.AddOption(k)
        # g2.SetDefaultString(keys[0])
        # g2.AcceptNothing(True)
        while True:
            result = g2.Get()
            if result == Rhino.Input.GetResult.Cancel:
                pass
            else:
                selected_key = g2.Option().EnglishName
                if selected_key in sc.sticky.keys():
                    sc.sticky[selected_key] = {}

            break

    elif result0 == "ShowAll":
        print(sc.sticky)
    elif result0 == "ClearAll":
        g3 = Rhino.Input.Custom.GetOption()
        g3.SetCommandPrompt("Are you sure?")
        for k in ["Yes", "No"]:
            g3.AddOption(k)
        g3.SetDefaultString("No")
        g3.AcceptNothing(True)
        while True:
            result = g3.Get()
            if result == Rhino.Input.GetResult.Cancel:
                pass
            else:
                confirm = g3.Option().EnglishName
                if confirm == "Yes":
                    sc.sticky = {}
                    break
                else:
                    pass

    else:
        pass
