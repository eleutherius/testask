DictOfPictures = {"Circle": "тут должен быть русунок круга", "Ellipse": "тут должен быть русунок круга",
                  "Triangle": "тут должен быть русунок треугольника", "IsoscelesTriangle": "тут должен быть русунок треугольника",
                  "EquilateralTriangle" : "тут должен быть русунок треугольника", "Rectangle":"прямоугольника",
                  "Square" : "тут должен быть русунок квадрата"
                  }

class BaseClass():
    def __init__(self):
        self.picture = ''
    def Space(self):
        print ('Space')
    def Perimeter(self):
        print('Perimeter')
    def Printing(self):
        print (DictOfPictures.get(self.__class__.__name__))
        print (self.__class__.__name__)

class Circle(BaseClass):
    def __init__(self, radius):
        self.radius =  radius
        self.pi = 3.14
        self.picture = DictOfPictures.get('circle')
    def Space(self):
        return self.pi * self.radius**2
    def Perimeter(self):
        return 2*self.pi*self.radius

class Ellipse(Circle):
    def __init__(self, radius1:float, radius2:float):
        super().__init__(radius1)
        self.radius2 = radius2
        self.picture = DictOfPictures.get ('ellipse')
    def Space(self):
        return self.pi * self.radius * self.radius2
    def Perimeter(self):
        return self.pi * (self.radius2 + self.radius)

class Square(BaseClass):
    def __init__(self, a):
        self.a = a
        self.picture = DictOfPictures.get ('square')
    def Space(self):
        return self.a**2
    def Perimeter(self):
        return self.a*4
class Rectangle(Square):
    def __init__(self, a, b):
        super().__init__(a)
        self.b = b
    def Space(self):
        return self.a * self.b
    def Perimeter(self):
        return (self.a * 2) + (self.b * 2)


class Triangle(BaseClass):
    def __init__(self, a, b,c):
        self.a = a
        self.b = b
        self.c = c

    def Space(self):
        p = 1/2 * (self.a + self.b + self.c)
        S = (p*(p - self.a)*(p - self.b)*(p - self.c)) ** 0.5
        return S
    def Perimeter(self):
        return self.a + self.b + self.c

class IsoscelesTriangle (Triangle):
    def __init__(self , a, b):
        self.a = a
        self.b = a
        self.c = b


class EquilateralTriangle(Triangle):
    def __init__(self, a):
        self.a = a
        self.b = a
        self.c = a


OBJ = EquilateralTriangle(5)

print (OBJ.Perimeter())
print (OBJ.Space())
print (OBJ.Printing())