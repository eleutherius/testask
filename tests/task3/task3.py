from ..library import TestCase
from testcase.testflow import executable
from atl.utils.sequences import Namespace
from ipmp.setup import getLocalIP, getFreePort
from ipmp.pages import GuiApi
import json
import os
from ipmp.emu.third_party import PushReceiverSms
from ipmp.interactive.rest.client import RestAPIClient, RestInstaller

_ALIAS_ = 'MyRestTests'


class Data(Namespace):

    def __init__(self):
        self.group_name = "New group"
        self.group_id: str
        self.psp_panel_id: str
        self.psp_panel_serial: str = "C10070010101"
        self.rest_client: str = "alexli10@visonic.ua"
        self.installer_client: str = "installer_client1"
        self.user_code = '1111'

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

    def AddPmaxPanel_Test(self):
        self.AddMessage('Add Pmax panel manually')
        self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
        whoami = self.GuiApi.Login.whoami()
        self.AssertTrue(whoami, 'Not OK', 'OK')

        resp = self.GuiApi.Units.add(unt_serial="A3B1B3", unt_account="005678", unt_name="03B1B3",
                                     _unt_module_gprs=True, _unt_module_bba=False, utg_id=int("1"),
                                     vendor='POWER_MASTER')
        self.AssertTrue(resp.json(), 'Failure', 'Success!!!')


@executable(context=Data)
class ChangeGroup(TestCase):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(ChangeGroup, self).__init__(*args, **kwargs)
    def changeGroupForPanel_Test(self):
        self.AssertLoginWasSuccess()
        self.AddMessage(f"Move panel {self.data.psp_panel_serial} to {self.data.group_name} group")
        panelId = self.GuiApi.Units.getUnitId(unt_serial=self.data.psp_panel_serial)
        groupId = self.GuiApi.Group.getGroupId(group_name=self.data.group_name)
        changeGroup = self.GuiApi.Units.change_unit_group(groupId=groupId, unitId=[panelId])
        self.CheckResponseCodeStatusSuccess(changeGroup, exp_code=200, status='success')
        self.AssertTrue(changeGroup, 'Not OK', 'OK')

@executable(context=Data)
class WakeupBroker(TestCase):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(WakeupBroker, self).__init__(*args, **kwargs)

    def setup_sms_broker_Test(self):
        self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
        self.AddMessage('Configure server')
        # self.SSH.addRowToHostsFile('127.0.0.1 comunicasms.orange.es')
        # resp = self.GuiApi.MMI.setupSmsBrokerConf('Orange', '21', '', '', '')
        self.GuiApi.MMI.selectMessageBrokerForWakeUp('Orange')

        # self.GuiApi.MMI.setupSmsBrokerConf('Bluerange', 2198, 'login', 'password', '1234567')
        self.SSH.enableSmsNotification()
        self.GuiApi.MMI.selectMessageBrokerForNotification('Bluerange')
        self.SSH.restartNginx()

@executable(context=Data)
class RegisterPowerUser(TestCase):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(RegisterPowerUser, self).__init__(*args, **kwargs)

    def create_rest_client(self, serial: str, email: str, pwd_to_panel: str = '1111'):
        client = RestAPIClient(self.connection.hostname, '12345', serial, pwd_to_panel, version='8.0',
                               format='json', logger=self.connection.logger)
        client.email = email
        client.password = 'Password*1'
        return client

    def set_grant_access(self, master_client, email, user_number):
        self.AddMessage('Set grand access user: %s, number %d' % (email, user_number))
        cmd = master_client.getCMD('grant_access')
        response = master_client.post(cmd=cmd, **{'email': email, 'user': user_number})
        self.AssertResponseCode(response, 204)

    def _registerPowerUser(self, client):
        '''
        :type client: RestAPIClient
        '''
        user = self.SSH.getPowerUserID(client.email)
        if not user:
            self.AddMessage('Register user %s' % client.email)
            response = client.register()
            self.AssertResponseCode(response, 204)
            # register_msg = self.CheckEmail(self.getEmailSender(), 'Registration')
            # code = self.getCodeFromMail(register_msg)
            # self.AddMessage('Complete register user')
            self.AddMessage('Complete register user')
            code = self.SSH.getPowerUserPruToken(client.email)
            self.AddMessage(f'User token : {code}')
            response = client.complete_register(code)
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
            self.AddMessage('Set password for user')
            response = client.setPassword()
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
        else:
            self.AddSuccess('User "%s" has already registered' % client.email)


    def RegisterPowerUser_Test(self):
        '''
        :type client: RestAPIClient
        '''

        # email = "alexli8@visonic.ua"
        master_client = self.create_rest_client(self.data.psp_panel_serial, self.data.rest_client,
                                                pwd_to_panel=self.data.user_code)
        self._registerPowerUser(master_client)
