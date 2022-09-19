import rhinoscriptsyntax as rs
import Rhino

"""
Tool for editing attributes of objects in a Rhino document (RhinoDoc.Objects).

These attibutes are stored in object name (string) as a dictionary with a certain formatting, for example:
"key1:value1_key2:value2" 
i.e. "_" separates entries and ":" separates key and value.

If selected object have such attributes, a pop-up window appears where they can be edited.
If objects have different values, it is shown as "Diverse", and can be overwritten with a common value.

After editing, the new values are saved back in objects' names. 
Objects with no name or improperly formatted are omitted.
"""
attr_dict_template = {
    'category': '',
    'width': '',
    'height': '',
    'zaxis': ''
    }


class RhObject(object):
    def __init__(self,rh_obj):
        self.rh_obj = rh_obj
        self.dict = self.get_attrs()

    def get_attrs(self,entrydivisor="_", defdivisor=":"):
        """
        Purpose:Extract dict from string  _key:value_....
        in:Rhino Guid
        out:Name dictionary
        """
        obj_name = rs.ObjectName(self.rh_obj)
        if not obj_name: 
            print("Object has no name")
            return attr_dict_template
        else:
            return generate_dict(obj_name)

    def set_attrs(self,dic):
        name = generate_name(dic)
        rs.ObjectName(self.rh_obj,name)

class RhAttributes(object):

    def __init__(self,rh_objs):
        if not rh_objs:
            print "No objects found"
            return
        rh_objs = [RhObject(x) for x in rh_objs]
        main_dict = self.read(rh_objs)
        self.write(rh_objs,main_dict)
        
    def write(self,objs,main_dict):
        for obj in objs:
            if not obj.dict: continue

            for key,value in obj.dict.iteritems():  
                
                if main_dict[key]=="various":
                    continue #move to the next iteration of the loop
                else:
                    obj.dict[key]=main_dict[key] #overwrites obj's value with a (newly set, or old, if same as others) common value for all elements
            
            str_name = generate_name(obj.dict)
            rs.ObjectName(obj.rh_obj,str_name)

    def read(self,objs):
        main_dict = {}
        for k in attr_dict_template.keys(): main_dict[k]=None
        for obj in objs:
            #if not obj.dict: continue
            for key,value in obj.dict.items():
                if key not in main_dict.keys(): continue
                if main_dict[key] == None: main_dict[key]=value
                elif main_dict[key] in (value,"various"): continue
                else: main_dict[key]="various"

        #abort if dictionary is empty
        if not bool(main_dict):
            return None
            
        #sort dict for list box display
        keylist=main_dict.keys()
        keylist.sort()
        valuelist=[]
        for key in keylist:
            valuelist.append(main_dict[key])

        #more info: https://developer.rhino3d.com/api/rhinoscript/user_interface_methods/propertylistbox.htm
        #Rhino.PropertyListBox (arrItems, arrValues [, strMessage [, strTitle [, arrPos]]])
        #values = rs.PropertyListBox(keylist,valuelist, "List of Items & Attributes", "Attributes")
        
        #Rhino.UI.Dialogs.ShowPropertyListBox(title, message, items, values)
        values = Rhino.UI.Dialogs.ShowPropertyListBox("Attributes", "List of Items & Attributes", keylist,valuelist)
        
        
        #here you can change values in the list box
        values = [cast_str(x) for x in values]
        for i,k in enumerate(keylist):
            main_dict[k]=values[i]
            
        return main_dict    
        
        
        
###HELPING FUCTIONS###
def generate_name(name_dict,entrydivisor="_", defdivisor=":"):
    """
    Purpose: Generate a namestring from a dictinary 
    in: Dictionary of keys/values
    return: String of  _key:value_....
    """
    name=""
    
    list = name_dict.keys()
    list.sort()
    for key in list:
        value=name_dict[key]
        name+=entrydivisor+str(key)+defdivisor+str(value)
 
    return name

def generate_dict(str,entrydivisor="_", defdivisor=":"):
    """
    Purpose: Generate a  dictinary from a name string
    in: String of  _key:value_....
    return: Dictionary of keys/values
    """
    data = str.split(entrydivisor)
    dic={}
    if len(data)>1:
        for d in data:
            a = d.split(defdivisor)
            if len(a)==2:
                key = a[0]
                value = a[1]
                dic[key]=value

    return cast_dict(dic)

def cast_str(s):
        """
        Cast given string into numbers and arrays (sketchy....)
        """
        allowed_chars = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_- /;')
        #Check if integer
        #if s.isdigit(): return int(s)
        #Check if set is string
        if set(s).issubset(allowed_chars):return s
        #filter for arrays and floats
        try:return s#eval(s)
        except:raise Exception("Casting of %s failed"%s)        

def cast_dict(dic):
        """
        Cast given string into numbers and arrays (sketchy....)
        """        
        for k,v in dic.iteritems():
                dic[k] = cast_str(v)
        return dic

if __name__=="__main__":

    objs = rs.GetObjects("Select objects to display attributes",0,False,True,True)
    if objs:
        at = RhAttributes(objs)
