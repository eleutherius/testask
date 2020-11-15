"""Задачки:"""

task1_1 = """1. Получить список всех нечётных чисел на отрезке [a, b]."""
task1_2 = """2. Получить список всех чисел Фибоначчи на отрезке [a, b]."""
task1_3 = """3. Напишите функцию, которая принимает на вход два параметра: a и b.
 - если тип обоих переменных (a и b) - int, вывести большее из них
 - если тип обоих переменных строка - сообщить, является ли строка b подстрокой строки a
 - если переменные разного типа, вывести сообщение об ошибке (любое)"""
task1_4 = """4. Напишите функцию, которая принимает на вход три параметра: начальный год (a), конечный год (b), список годов (c). функцию должна вернуть список високосных лет между а і b, кроме тех которые указаны у списку c."""
task1_5 = """5. Найти сумму элементов массива."""
task1_6 = """6. Найти максимальный элемент, значение и индекс."""
task1_7 = """7. Найти минимальный элемент, значение и индекс."""
task1_8 = """8. Посчитать количество элементов больше нуля."""
task1_9 = """9. Прибавить к элементам массива их индекс."""
task1_10 = """10. Циклический сдвиг элементов массива на k- позиций вправо."""
task1_11 = """11. Вывести элементы одного массива, которые не равны элементам второго массива."""
task1_12 = """12. Из двух отсортированных массивов сделать третий отсортированный, не сортируя его."""

"""ООП"""

task2_1 = """1. Создать базовый клас который описывает геометрическую фигуру (можно абстрактный). Так же нужно создать класы которые описывают эллипс, круг, треугольник, равнобедренный треугольник, равносторонний треугольник, прямоугольник, квадрат. Все классы должны иметь методы вычисления площади и периметра."""
task2_2 = """2. Создать структуру данных типа дерево. Каждый узел дерева должен иметь строковое представление в виде "путь к вершине". Имплементировать методы который позволяют:
обходить дерево горизонтально и вертикально
добавлять элементы в дерево
делать вставку узла дерева.
выполнять поиск по атрибуту узла дерева"""

task2_3 = """3. Написать юнит тесты для кода из задачи про структуру данных типа дерево."""


def printing(task: str):
    print("#" * 80)
    print(f"Задача: {task}")
    print("#" * 80)
    print("Решение:")


printing(task1_1)

a, b = 10, 87
print(f"Допустим a = {a}, b = {b}")
list1 = []
for i in range(a, (b + 1)):
    if i % 2 > 0:
        list1.append(i)
print(list1)

printing(task1_2)


def _fibonacci(a, b):
    out_list = []
    fibonacci = []
    for n in range(0, b):
        if n == 0:
            fibonacci.append(0)
        if n == 1:
            fibonacci.append(1)
        if n > 1:
            fibonacci.append(fibonacci[n - 1] + fibonacci[n - 2])
    for i in fibonacci:
        if i >= a and i <= b:
            out_list.append(i)
    return out_list


a = 0
b = 100
print(_fibonacci(a, b))

printing(task1_3)


def check_types(a, b):
    if type(a) is int and type(b) is int:
        print(max(a, b))
    elif type(a) is str and type(b) is str:
        if b in a:
            print("b is sub str of the a")
        else:
            print("b is not sub str of the a")
    elif type(a) != type(b):
        print("Error!")


a = 10
b = 15
check_types(a, b)
a = "firs str"
b = "second str"
check_types(a, b)
a = "str"
b = 100
check_types(a, b)

printing(task1_4)


def year_calc(start_year: int, end_year: int, list_of_years: list):
    internul_list = []
    for i in range(start_year, end_year + 1):
        if i % 4 == 0:
            if i % 100 != 0:
                internul_list.append(i)
            elif i % 100 == 0 and i % 400 == 0:
                internul_list.append(i)
    return list(set(internul_list) - set(list_of_years))


start_year = 100
end_year = 2020
list_of_years = [1800, 1900]
print(year_calc(start_year, end_year, list_of_years))

printing(task1_5)
arr = ['32', '3', '3', '24', '32', '24', '2', '2', '2', '24']
print(sum((int(arr[i]) for i in range(0, int(len(arr))))))

printing(task1_6)
print(f"Минимальный элемент: {max(arr)}")
print(f"Индекс минимального элемента: {arr.index(max(arr))}")
printing(task1_7)
print(f"Минимальный элемент: {min(arr)}")
print(f"Индекс минимального элемента: {arr.index(min(arr))}")
printing(task1_8)

counter = 0
for i in arr:
    if int(i) > 0:
        counter = counter + 1
print(f"Количество элементов больше нуля:{counter}")

printing(task1_9)


# Способ 1
def shift(lst, k):
    for i in range(k):
        last = lst.pop()
        lst.insert(0, last)


a = [1, 0, 100, -20]
shift(a, 2)
print(f'Результат спасоба 1 {a}')

# Способ

from collections import deque

a = [1, 0, 100, -20]
k = 2
d = deque(a)
d.rotate(k)
result = list(d)
print(f'Результат спасоба 2 {result}')

printing(task1_10)


def shift(m_array, steps):
    for i in range(steps):
        m_array.insert(0, m_array.pop())


shift(arr, 1)
print(f'Сдвиг вправо: {arr}')

printing(task1_11)

arr1 = [1, 2, 3, 4, 5]
arr2 = [3, 4, 7, 9, 105]
print(set(arr1) - set(arr2))

printing(task1_12)

c = arr1 + arr2
print(f'Отсортированный массив : {sorted(c)}')

printing(task2_1)

DictOfPictures = {"Circle": "тут должен быть русунок круга", "Ellipse": "тут должен быть русунок круга",
                  "Triangle": "тут должен быть русунок треугольника",
                  "IsoscelesTriangle": "тут должен быть русунок треугольника",
                  "EquilateralTriangle": "тут должен быть русунок треугольника", "Rectangle": "прямоугольника",
                  "Square": "тут должен быть русунок квадрата"
                  }


class BaseClass():
    def __init__(self):
        pass

    def Space(self):
        print('Space')

    def Perimeter(self):
        print('Perimeter')

    def Printing(self):
        print(DictOfPictures.get(self.__class__.__name__))


class Circle(BaseClass):
    def __init__(self, radius):
        self.radius = radius
        self.pi = 3.14

    def Space(self):
        return self.pi * self.radius ** 2

    def Perimeter(self):
        return 2 * self.pi * self.radius


class Ellipse(Circle):
    def __init__(self, radius1: float, radius2: float):
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
        super().__init__(a, a)


class Triangle(Rectangle):
    def __init__(self, a, b, c):
        super().__init__(a, b)
        self.c = c

    def Space(self):
        p = 1 / 2 * (self.a + self.b + self.c)
        S = (p * (p - self.a) * (p - self.b) * (p - self.c)) ** 0.5
        return S

    def Perimeter(self):
        return self.a + self.b + self.c


class IsoscelesTriangle(Triangle):
    def __init__(self, a, b):
        super().__init__(a, a, b)


class EquilateralTriangle(Triangle):
    def __init__(self, a):
        super().__init__(a, a, a)


printing(task2_2)


class Bunch(dict):
    def __init__(self, *args, **kwds):
        super(Bunch, self).__init__(*args, **kwds)
        self.__dict__ = self


T = Bunch
t = T(left=T(left="a", right="b"), right=T(left=T(left=T(left="q", right="z"), right="y")))


def vertical(dict1):
    for k, v in dict1.items():

        if type(v) == str:
            print(f"key: {k} value: {v}")
        elif type(v) == Bunch:
            vertical(v)


def horizontal(dict1, var1):
    for k, v in dict1.items():
        if var1 == k and type(v) != Bunch:
            print("horizontal", k, v)
        elif var1 == k and type(v) == Bunch:
            horizontal(v, var1)


vertical(t)
horizontal(t, "left")

# printing(task2_3)
