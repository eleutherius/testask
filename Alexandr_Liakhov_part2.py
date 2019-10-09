#По теории читаем и знакомимся по книге с класами объектами и основами ООП.
"""
Задача1: создать базовый клас который описывает геометрическую фигуру (можно абстрактный).
Так же нужно создать класы которые описывают элипс, круг, треугольник, равнобедренный треугольник,
равносторонний треугольник, прямоугольник, квадрат. Все классы должны иметь методы вычисления площади и
периметра.
"""
DictOfPictures = {"Circle": "тут должен быть русунок круга", "Ellipse": "тут должен быть русунок круга",
                  "Triangle": "тут должен быть русунок треугольника", "IsoscelesTriangle": "тут должен быть русунок треугольника",
                  "EquilateralTriangle" : "тут должен быть русунок треугольника", "Rectangle":"прямоугольника",
                  "Square" : "тут должен быть русунок квадрата"
                  }

class BaseClass():
    def __init__(self):
        pass
    def Space(self):
        print ('Space')
    def Perimeter(self):
        print('Perimeter')
    def Printing(self):
        print (DictOfPictures.get(self.__class__.__name__))

class Circle(BaseClass):
    def __init__(self, radius):
        self.radius =  radius
        self.pi = 3.14
    def Space(self):
        return self.pi * self.radius**2
    def Perimeter(self):
        return 2*self.pi*self.radius

class Ellipse(Circle):
    def __init__(self, radius1:float, radius2:float):
        super().__init__(radius1)
        self.radius2 = radius2
    def Space(self):
        return self.pi * self.radius * self.radius2
    def Perimeter(self):
        return self.pi * (self.radius2 + self.radius)

class Rectangle(BaseClass):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def Space(self):
        return self.a * self.b
    def Perimeter(self):
        return (self.a * 2) + (self.b * 2)

class Square(Rectangle):
    def __init__(self, a):
        super ( ).__init__ (a,a)

class Triangle(Rectangle):
    def __init__(self, a, b,c):
        super().__init__(a,b)
        self.c = c
    def Space(self):
        p = 1/2 * (self.a + self.b + self.c)
        S = (p*(p - self.a)*(p - self.b)*(p - self.c)) ** 0.5
        return S
    def Perimeter(self):
        return self.a + self.b + self.c

class IsoscelesTriangle (Triangle):
    def __init__(self , a, b):
        super ( ).__init__ (a,a,b)

class EquilateralTriangle(Triangle):
    def __init__(self, a):
        super ( ).__init__ (a,a,a)

"""
Задача3: Логирование. Необходимо реализовать логирование при помощи классов. 
Класс логирования должен обеспечивать возможность как записи в текстовьій файл,
так и вьівод на консоль и оба. В зависимости от переданного параметра.
Простор для творчества ваш. 
Форматирование не обязательно, достаточно вьіводить время, помимо сообщения.
Внимание, использовать стандартную библиотеку нельзя.Со звездочкой ;)
P.S. Копировать решение из стандартной библиотеке - не красиво в плане обучения. Либо решайте сами, либо пропускайте задачу.
"""
import datetime
import inspect
# print (inspect.currentframe().f_back.f_lineno)

from inspect import currentframe, getframeinfo
frameinfo = getframeinfo(currentframe())



class log:
    def __init__(self, path='./logs.txt', LEVEL="INFO"):
        self.path = path
        self.LEVEL = LEVEL

    def formatting(self, time, msg,  err=False):
        Red = '\033[91m'
        Green = '\033[92m'
        END = '\033[0m'

        if err:
            print (f"{Red}{time} - {msg} {END}")
        else:
            print (f"{Green}{time} - {msg} {END}")

    def writing(self, time, msg):
        with open (self.path, "a") as f:
            f.write(f"{time} - {msg} \n")

    def logining(self, msg=None):
        if self.LEVEL == "INFO":
            time = datetime.datetime.now ( ).strftime ("%Y-%m-%d-%H.%M.%S")
            self.formatting(time, msg)
        if self.LEVEL == "ALERT":
            time = datetime.datetime.now ( ).strftime ("%Y-%m-%d-%H.%M.%S")
            self.formatting(time, msg)
        if self.LEVEL == "WARNING":
            time = datetime.datetime.now ( ).strftime ("%Y-%m-%d-%H.%M.%S")
            self.writing(time, msg)
        if self.LEVEL == "CRITICAL":
            time = datetime.datetime.now ( ).strftime ("%Y-%m-%d-%H.%M.%S")
            self.writing(time, msg)
            self.formatting(time, msg, err=True)
        if self.LEVEL == "DEBUG":
            time = datetime.datetime.now ( ).strftime ("%Y-%m-%d-%H.%M.%S")
            self.writing(time, msg)
            self.formatting(time, msg, err=True)


mylog = log (LEVEL="DEBUG")
msg = "Some info message"
mylog.logining(msg=f'{msg} - File [{frameinfo.filename}] Line : [{frameinfo.lineno}]')


"""
Задача4: напишите класс "Elevator" для предположим N этажного дома. объект данного класса должен уметь:
- перемещаться между этажами (без возможности провалиться в адъ, улететь в космос). скорость движения лифта - 1 этаж 
в секунду. соответственно с 1-го на 10-й он должен ехать 9 секунд
- не перемещаться, если лифт перегружен (разрешенный вес выберите сами)
- при каждом изменении состояния выводить в консоль текущий этаж
- print() на объекте должен выводить текущую информацию о лифте (этаж, загруженность)
- звёздочка* - реализуйте возможность экстренной остановки лифта на текущем этаже
- звёздочка* - реализуйте возможность подбирать людей при движении вниз. пример: если едем с эт.10 на эт.1,
 должна быть возможность остановить лифт на эт.5, после чего автоматически продолжить движение.
"""
import time
class Elevator():
    def __init__(self,  DefFloorNum=1):

        self.WeightMax = 500
        self.NumberOfFloor = 10
        self.FloorNum=DefFloorNum
    def run(self):
        n = abs(self.FloorNum - self.NumberOfFloor)
        if  n == 0:
            print (f'Floor #{self.FloorNum} Weight:{self.weight}')
        elif n > 0:
            print (f'Floor #{self.FloorNum} Weight:{self.weight}')
            time.sleep (1)
            try:
                for i in range(0, n):
                    if  self.NumberOfFloor - self.FloorNum  < 0 :
                        self.FloorNum -= 1
                    elif self.NumberOfFloor - self.FloorNum  > 0 :
                        self.FloorNum += 1
                    print (f'Floor #{self.FloorNum} Weight:{self.weight}')
                    time.sleep(1)
                # self.FloorNum = self.NumberOfFloor
            except KeyboardInterrupt:
                print (f"""**************************************************
                Interrupt!!!!!
                We are stop on the floor #{self.FloorNum}""")
    def InputFloor(self):
        Floor = int(input ("Input floor: "))
        if Floor >= 1 and Floor <= 10:
            self.Weight(int(input ("Weight: ")))
            self.NumberOfFloor = Floor
            self.run()

        else:
            print ("Wrong input")
    def Weight (self, weight):
        self.weight = weight
        if weight > 0:
            if self.weight > self.WeightMax:
                print ("Wrong Waigt")
                exit(1)
        if weight < 0:
            if self.weight < 0:
                print ("Wrong Waigt")
                exit(1)


lift  = Elevator(DefFloorNum=1)
lift.InputFloor()
lift.InputFloor()

"""
Задача5: реализуйте класс "BrokenCalc", у которого неправильно работают все функции
пример вызова: brocen_calc_instance.function(arg1, arg2)
перечень неисправностей:
сложение - возвращает разность
вычитание - сумму
деление - возвращает первое число в степени второго
умножение двух чисел - строку, скомпонованную из них
возведение числа в степень должно поменять местами число и степень, и вернуть вычисленный результат("2 в степени 3" должно вернуть "3 в степени 2" = 9)
корень из числа всегда возвращает ноль

звёздочка*: реализации методов сложения, вычитания, умножения должны уметь работать с любым количеством входных аргументов:

>>> brocen_calc_instance.add(2, 3, 4, 5, 6) # 2 - 3 - 4 - 5 - 6
<<< -16
"""

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
