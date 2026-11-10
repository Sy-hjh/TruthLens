import math

def logit(value):
 p=min(1-1e-5,max(1e-5,float(value)));return math.log(p/(1-p))

def fusion(first,second,coefficients):
 z=coefficients[0]*logit(first)+coefficients[1]*logit(second)+coefficients[2]
 return 1/(1+math.exp(-max(-30,min(30,z))))
