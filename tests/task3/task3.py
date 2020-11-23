from ..library import TestCase
from testcase.testflow import executable
from atl.utils.sequences import Namespace
from ipmp.pages import GuiApi
import json

_ALIAS_ = 'MyRestTests'


class Data(Namespace):

    def __init__(self):
        self.group_name = "New group"
        self.group_id: str
        self.psp_panel_id: str
        self.psp_panel_serial: str = "C10070010101"
        pass


"""
1. Create a group, add two panels (pmax, neo), choose new group for neo panel.
2. Choose a different sms broker for wakeup and notifications.
3. Register rest client and installer complete registration ,  delete these users.
"""


@executable(context=Data)
class AddGroups(TestCase):

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(AddGroups, self).__init__(*args, **kwargs)

    def CreateGroup_Test(self):
        self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
        whoami = self.GuiApi.Login.whoami()
        self.AssertTrue(whoami, 'Not OK', 'OK')
        self.AddMessage(whoami.json()['data']['permissions'])
        resp = self.GuiApi.Group.addGroup("New group")
        self.AssertTrue(resp.json()['status'] == 'success', 'Failure', 'Success!!!')
        # self.AddMessage(resp.json())
        self.data.group_id = resp.json()['data']['utg_id']

@executable(context=Data)
class AddPanels(TestCase):

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(AddPanels, self).__init__(*args, **kwargs)

    def AddPspPanel_Test(self):
        self.AddMessage('Add PSP panel manually')
        self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
        whoami = self.GuiApi.Login.whoami()
        self.AssertTrue(whoami, 'Not OK', 'OK')
        resp = self.GuiApi.Units.add(unt_serial=self.data.psp_panel_serial, unt_account="7541FF",
                                     unt_name=self.data.psp_panel_serial, utg_id=int("1"), vendor='NEO',
                                     _unt_module_gprs='offline', _unt_module_bb='offline')
        self.AssertTrue(resp.json()['status'] == 'success', 'Failure', 'Success!!!')

        p_id = self.GuiApi.Units.getUnitId(unt_serial=self.data.psp_panel_serial)
        # self.AddMessage(type(self.data.psp_panel_id))
        change_group = self.GuiApi.Units.change_unit_group(groupId=self.data.group_id,
                                                           unitId=[p_id])
        # self.AssertTrue(change_group, 'Not OK', 'OK')
        self.AddMessage(change_group)


    def AddPmaxPanel_Test(self):
        self.AddMessage('Add Pmax panel manually')
        self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
        whoami = self.GuiApi.Login.whoami()
        self.AssertTrue(whoami, 'Not OK', 'OK')

        resp = self.GuiApi.Units.add(unt_serial="A3B1B3", unt_account="005678", unt_name="03B1B3",
                                     _unt_module_gprs=True, _unt_module_bba=False, utg_id=int("1"),
                                     vendor='POWER_MASTER')
        self.AssertTrue(resp.json(), 'Failure', 'Success!!!')


# @executable(context=Data)
# class TestTask3_2(TestCase):
#
#     def __init__(self, data, *args, **kwargs):
#         self.data = data
#         super(TestTask3_2, self).__init__(*args, **kwargs)
#
#     def ChangeGroup_Test(self):
#         self.AddMessage('Add Pmax panel manually')
#         self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
#         whoami = self.GuiApi.Login.whoami()
#         self.AssertTrue(whoami, 'Not OK', 'OK')
#         # resp = self.GuiApi.Units.get_all_units
#         # self.AddMessage(resp)

