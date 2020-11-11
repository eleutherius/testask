from ..library import TestCase
from testcase.testflow import executable
from atl.utils.sequences import Namespace

_ALIAS_ = 'MyTests'


class Data(Namespace):

    def __init__(self):
        pass


"""
1. Написати тести з використанням всіх видів перевірок (ExpectTrue, ExpectNone, etc.).
2. Написати тести в яких не проходить перевірка AssertTrue на наступних етапах:
    • Environment.Create
    • Environment.Remove
    • CreateEnvironment
    • RemoveEnvironment
    • Setup
    • Close
    • Test
3. Написати тести з використанням всіх типів повідомлень в юзер лог.
4. Написати тести з використанням всіх типів повідомлень в automation лог. * Додати пераметр в TMC, яким можна буде вказати рівень логування для тестів.

Всі тести писати можна писати прості, типу 2!=3 і так далі. 

Основна вимога, тести мають бути в одному файлі в різних класах і мають бігти в TMC.
"""

@executable(context=Data)
class TestTask2_1(TestCase):
    """
    1. Написати тести з використанням всіх видів перевірок (ExpectTrue, ExpectNone, etc.).
    """
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_1, self).__init__(*args, **kwargs)
    
    def Setup(self): pass

    def Close(self): pass

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self): pass

    def Dummy_Test(self):
        self.AddMessage('ExpectTrue check')
        self.ExpectTrue(1 == 1, 'Failure', 'Success')
        self.AddMessage('ExpectTrue check')
        self.ExpectTrue(1 == 2, 'Failure', 'Success')
        self.AddMessage('ExpectNone check')
        self.ExpectNone(None, 'Failure', 'Success')
        self.AddMessage('ExpectNotNone check')
        self.ExpectNotNone(None, 'Failure', 'Success')
        self.AddMessage('ExpectNotTrue check')
        self.ExpectNotTrue(1 == 2, 'Failure', 'Success')
        self.AddMessage('ExpectResponseCode check')
        self.ExpectResponseCode(200, 404)

@executable(context=Data)
class TestTask2_2_1(TestCase):
    """
    2. Написати тести в яких не проходить перевірка AssertTrue на наступних етапах:
    • Environment.Create
    • Environment.Remove
    • CreateEnvironment
    • RemoveEnvironment
    • Setup
    • Close
    • Test
    """
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_2_1, self).__init__(*args, **kwargs)
    
    def Setup(self): pass

    def Close(self): pass

    def CreateEnvironment(self):
        self.AddMessage('Тест в яких не проходить перевірку AssertTrue на CreateEnvironment етап')
        self.AssertTrue(1 == 2, 'Failure', 'Success')

    def RemoveEnvironment(self): pass

    def test_Test(self): pass


@executable(context=Data)
class TestTask2_2_2(TestCase):
    """
    2. Написати тести в яких не проходить перевірка AssertTrue на наступних етапах:
    • Environment.Create
    • Environment.Remove
    • CreateEnvironment
    • RemoveEnvironment
    • Setup
    • Close
    • Test
    """

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_2_2, self).__init__(*args, **kwargs)

    def Setup(self): pass

    def Close(self): pass

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self):
        self.AddMessage('Тест в яких не проходить перевірку AssertTrue на RemoveEnvironment етап')
        self.AssertTrue(1 == 2, 'Failure', 'Success')

    def test_Test(self): pass

@executable(context=Data)
class TestTask2_2_3(TestCase):
    """
    2. Написати тести в яких не проходить перевірка AssertTrue на наступних етапах:
    • Environment.Create
    • Environment.Remove
    • CreateEnvironment
    • RemoveEnvironment
    • Setup
    • Close
    • Test
    """

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_2_3, self).__init__(*args, **kwargs)

    def Setup(self):
        self.AddMessage('Тест в яких не проходить перевірку AssertTrue на Setup етап')
        self.AssertTrue(1 == 2, 'Failure', 'Success')

    def Close(self): pass

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self): pass

    def test_Test(self): pass


@executable(context=Data)
class TestTask2_2_4(TestCase):
    """
    2. Написати тести в яких не проходить перевірка AssertTrue на наступних етапах:
    • Environment.Create
    • Environment.Remove
    • CreateEnvironment
    • RemoveEnvironment
    • Setup
    • Close
    • Test
    """

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_2_4, self).__init__(*args, **kwargs)

    def Setup(self): pass

    def Close(self):
        self.AddMessage('Тест в яких не проходить перевірку AssertTrue на Close етап')
        self.AssertTrue(1 == 2, 'Failure', 'Success')

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self): pass

    def test_Test(self): pass


@executable(context=Data)
class TestTask2_3(TestCase):
    """
    3. Написати тести з використанням всіх типів повідомлень в юзер лог.
    """
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_3, self).__init__(*args, **kwargs)
    
    def Setup(self): pass

    def Close(self): pass

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self): pass

    def AllTypesUserLogs_Test(self):
        self.AddMessage('User message type , "Message"')
        self.AddWarning('User message type , "Warning"')
        self.AddFailure('User message type , "Failure"')



@executable(context=Data)
class TestTask2_4(TestCase):
    """
    4. Написати тести з використанням всіх типів повідомлень в automation лог. * Додати пераметр в TMC, яким можна буде вказати рівень логування для тестів.
    """
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask2_4, self).__init__(*args, **kwargs)
    
    def Setup(self): pass

    def Close(self): pass

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self): pass
    
    def AllTypesAutomationLogs_Test(self):
        self.connection.logger.debug('Print to automation log')
        self.connection.logger.info('Print to automation log')
        self.connection.logger.warning('Print to automation log')
        self.connection.logger.error('Print to automation log')