"""
TASK #1

Світлана замовляє чашки для співробітників, на яких мають бути надруковані імена.
Напишіть будь ласка функцію, що приймає на вхід список людей, у якому кожна людина описана як словник  ключами “name”, “surname”.
А повертає структуру з іменами і кількістю чашок які потрібно замовити.
"""
from array import array
from collections import Counter
test_list = [{'name': 'Alex', 'surname':'Liakhov'}, { 'name': 'Micola', 'surname' :'Liakhov1'}, { 'name': 'Alex', 'surname' :'Micola'}]
def NameCounter (var):
    names = []
    for i in var:
         names.append(i['name'])
    all = dict(Counter(names))
    all['Number of all cups'] = len (names)

    return all

# print(NameCounter(test_list))

"""
TASK #2

Написать метод который принимет два числа a, b и возвращает все числа Фибоначчи на отрезке [a, b]
"""
def Fibonacci (a, b):
    out_list = []
    fibonacci = []
    for n in range (0, b):
        if n == 0 :
            fibonacci.append(0)
        if n == 1:
            fibonacci.append(1)
        if n > 1:
            fibonacci.append(fibonacci[n -1] + fibonacci[n -2])
    for i in fibonacci:
        if i >= a and i <= b:

         out_list.append(i)
    return out_list

# print (Fibonacci(10, 100))

"""
TASK #3

получить список всех нечётных чисел от 0 до 100
со звёздочкой - сделайте это в одну строку
"""
# a = [ i for i in range(0, 100) if i%2 == 1]
# print (a)

"""
TASK #4

напишите метод, который принимает на вход два параметра: a и b
если тип обоих переменных (a и b) - int, вывести большее из них
если тип обоих переменных строка - сообщить, является ли строка b подстрокой строки a
если переменные разного типа, вывести сообщение об ошибке (любое)
"""
def MyFunction (a, b):
    if type(a) is int and type(b) is int:
         if a > b:
            print(a)
         if a < b:
            print (b)
    elif type(a) is str and type(b) is str:
        if b in a:
             print ('b is sub string of a')
        else:
            print('b is not sub  string of a')
    else:
        print ('ERRR! differend types')

# MyFunction ('hello', 'h')


"""
TASK #5

Напишіть функцію, яка приймає на вхід три параметри: початковий рік (a), кінцевий рік (b),
список років (c). Функція має попертати список високосних років між а і b, крім вказаних у c
"""

def IntercalaryYear(year):
    if year % 4 != 0 or (year % 100 == 0 and year % 400 != 0):
        pass
    else:
        return year
def Years (a,b,c):
    MySET=set()
    for i in range(a, b):
        MySET.add(IntercalaryYear(i))
    abc = MySET - set(c)
    return abc
c = [13, 12, 235, 1996]

# print (Years(1991, 2019, c))


"""
TASK #6

Несколько задачек на массивы данных: 
6.1
- Найти сумму элементов массива
"""

a = [1, 2, 3]
# print (f'Сумма элементов массива{b}')



# b = sum (a)
# print (f'Сумма элементов массива{b}')


"""
6.2
- Найти максимальный элемент, значение и индекс
"""
a = [1, 0, 100, -20]
MaxElement = max(a)
IndexMaxElement = a.index(max(a))
print ( f'Max element = {MaxElement}', f'Index of element = {IndexMaxElement}')




"""
6.3
- Найти минимальный элемент, значение и индекс
"""

a = [1, 0, 100, -20]
MinElement = min(a)
IndexMinElement = a.index(min(a))
print ( f'Max element = {MinElement}', f'Index of element = {IndexMinElement}')


b = 0
for i in range(len(a)):
    if i > 0 :
        b = b + 1
print (f'Количество элементов  больше нуля : {b}')

"""
6.4
- Посчитать количество элементов больше нуля
"""

a = [1, 0, 100, -20]
for i in range(len(a)):
    a[i]=a[i] + i
print (f'Результат: {a}')

"""
6.5
- Прибавить к элементам массива их индекс
"""

#Способ 1
def shift(lst, k):
    for i  in range(k):
        last = lst.pop()
        lst.insert(0, last)
a = [1, 0, 100, -20]
shift(a, 2)
print (f'Результат спасоба 1 {a}')

#Способ

from collections import deque
a = [1, 0, 100, -20]
k = 2
d = deque(a)
d.rotate(k)
result = list(d)
print (f'Результат спасоба 2 {result}')
"""
6.6
- Циклический сдвиг элементов массива на k- позиций вправо
"""
abc = [1, 2, 3, 4, 5]
def shift(lst, steps):
    for i in range(steps):
        lst.insert(0, lst.pop())
shift(abc, 1)
print (f'Сдвиг вправо: {abc}')
"""
6.7
- Вывести элементы одного массива, которые не равны элементам второго массива.
"""
a = a = [1, 2, 3, 4, 5]
b = [3, 4, 7, 9, 105]
result = set(a) - set (b)
print (result)

"""
6.8
- Из двух отсортированных массивов сделать третий отсортированный, не сортируя его
"""
a = [1, 2, 3, 4, 5]
b = [3, 4, 7, 9, 105]
c = a+b
print(f'Отсортированный массив : {sorted(c)}')


"""
TASK #7

Создать чать на pytnon 
"""
