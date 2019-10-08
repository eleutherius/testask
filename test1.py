from functools import reduce
# reduce(lambda x, y: x*y, *args)

class BrokenCalc():
    def __init__(self):
        pass
    def add (self, arg1, *args):
        for arg in args:
            arg1 -= arg
        return arg1
    def sub (self, arg1, *args):
        for arg in args:
            arg1 += arg
        return arg1
    def div (self, arg1, *args):
        for arg in args:
            arg1 *= arg
        return arg1
    def mult (self, arg1, *args):
        for arg in args:
            arg1 = arg ** arg1
        return arg1
    def square (self, arg1, *args):
        for arg in args:
            arg1 /= arg
        return arg1
    def root (self, arg1):
        return 0

myob = BrokenCalc()
print (myob.add(2, 3, 4, 5, 6))
print (myob.div(2, 3, 4, 5, 6))
print (myob.sub(2, 3, 4, 5, 6))
print (myob.mult(2, 3, 4, 5, 6))
print (myob.square(2, 3, 4, 5, 6))