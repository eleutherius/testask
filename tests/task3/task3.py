from ..library import TestCase
from testcase.testflow import executable
from atl.utils.sequences import Namespace

_ALIAS_ = 'MyRestTests'


class Data(Namespace):

    def __init__(self):
        self.new_group = "New group"
        pass


"""
1. Create a group, add two panels (pmax, neo), choose new group for neo panel.
2. Choose a different sms broker for wakeup and notifications.
3. Register rest client and installer complete registration ,  delete these users.
"""

from ipmp.pages import GuiApi


@executable(context=Data)
class TestTask3_1(TestCase):

    def __init__(self, data, *args, **kwargs):

        self.data = data
        super(TestTask3_1, self).__init__(*args, **kwargs)

    def Setup(self): pass

    def Close(self): pass

    def CreateEnvironment(self): pass

    def RemoveEnvironment(self): pass

    def CreateGroup_Test(self):
        self.AddMessage('Create group')
        self.gui_api = GuiApi(self.connection.hostname)
        self.AddMessage(f'Login to {self.connection.hostname}')
        self.gui_api.Login.login(usr_email=self.email_client.email, usr_password=self.email_client.password)
        self.AddMessage('some')
        resp = self.gui_api.Group.addGroup("New1")
        self.AddMessage(f"{self.data.new_group: resp.json()['data']['utg_id']}")


    def AddPspPanel_Test(self):
        self.AddMessage('Add PSP panel manually')

    def AddPmaxPanel_Test(self):
        self.AddMessage('Add Pmax panel manually')

    def ChangeGroupPsp_Test(self):
        self.AddMessage('Change group for PSP panel')



    # def create_group(self, name):
    #     self.gui_api.Login.login(usr_email=self.email, usr_password=self.passwd)
    #     resp = self.gui_api.Group.addGroup(name)
    #     return {name: resp.json()['data']['utg_id']}
    # def add_panels(self):
    #     self.gui_api.Login.login(usr_email=self.email, usr_password=self.passwd)
    #     # self.gui_api.Units.add()
    #     resp = self.gui_api.Units.add(unt_serial="A3B1B3", unt_account="005678", unt_name="03B1B3",
    #                                   _unt_module_gprs=True, _unt_module_bba=False, utg_id=int("1"), vendor='POWER_MASTER')
    #     print (resp.json()['Response'])
    #
    #     resp = self.gui_api.Units.add(unt_serial="C10070010101", unt_account="7541FF",
    #                                   unt_name="000070010101", utg_id=int("1"), vendor='NEO',
    #                                   _unt_module_gprs='offline',
    #                                   _unt_module_bb='offline')

from ipmp.setup import IpmpInitalSetup
from ipmp.emu.neo import NeoPanel
from ipmp.emu.pmax import PmaxPanel

# rutine  = Rutiner("94.125.123.58", "admin@tycomonitor.com", "Admin123")
# rutine.add_panels()
