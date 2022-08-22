from compas_timber.utils.workflow import JointDefinition

if B1 and B2:
    if len(B1)!=len(B2): raise UserWarning(" I need an equal number of Beams in B1 and B2.")
    TButt = []
    for beam1,beam2 in zip(B1,B2):
        TButt.append(JointDefinition('T-Butt', (beam1,beam2)))
