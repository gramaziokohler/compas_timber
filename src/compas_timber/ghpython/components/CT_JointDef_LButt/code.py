from compas_timber.utils.workflow import JointDefinition

if len(B1)==0 or len(B2)==0:
    pass
elif (len(B1)==1 and B1[0]==None) or (len(B2)==1 and B2[0]==None): 
    pass
else:
    if len(B1)!=len(B2): raise UserWarning(" I need an equal number of Beams in B1 and B2.")
    LButt = []
    for beam1,beam2 in zip(B1,B2):
        LButt.append(JointDefinition('L-Butt', (beam1,beam2)))
