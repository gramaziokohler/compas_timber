import Rhino

def update_rhinodocobject_name(guid,name,separator='_'):
    obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
    #att = Rhino.DocObjects.ObjectAttributes()
    att = obj.Attributes
    current_name = att.Name
    if current_name == None:
        att.Name = name
    else:
        att.Name = "%s%s%s"%(current_name, separator,name)
    obj.Attributes = att
    obj.CommitChanges()