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
        self.power_user: str = "alexli11@visonic.ua"
        self.user_code = '1111'
        self.pmax_serial = 'AC1234'
        self.pmax_account = '040892'
        self.pmax_installer_code = 9999
        self.pmax_user_code = '1111'
        # self.installer_rest_version = 6.0
        self.installer_email = "alexli58@visonic.ua"


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
        self.GuiApi.MMI.selectMessageBrokerForWakeUp('Orange')

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

    def _registerPowerUser(self, client):
        '''
        :type client: RestAPIClient
        '''
        user = self.SSH.getPowerUserID(client.email)
        if not user:
            self.AddMessage('Register user %s' % client.email)
            response = client.register()
            self.AssertResponseCode(response, 204)
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

        master_client = self.create_rest_client(self.data.psp_panel_serial, self.data.power_user,
                                                pwd_to_panel=self.data.user_code)
        self._registerPowerUser(master_client)


@executable(context=Data)
class RegisterInstallerUser(TestCase):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(RegisterInstallerUser, self).__init__(*args, **kwargs)

    def RegisterInstallerUser_Test(self):
        '''
        :type client: RestAPIClient
        '''
        installer_client = self.createInstallerClient(self.data.pmax_serial)
        self._registerInstallerUser(installer_client)

    def createInstallerClient(self, panel_serial: str, password: str = 'Password*1', ):
        version = self.rest_version.installer
        self.AddMessage(
            f'Create Installer Client version - {self.data.installer_rest_version}, serial panel - {panel_serial}')
        client = RestInstaller(ip=self.connection.hostname, email=self.data.installer_email, password=password,
                               panel_name=panel_serial, app_id='1234', panel_code='5555',
                               version=version, format='json', logger=self.connection.logger)
        return client

    def _registerInstallerUser(self, client: RestInstaller):
        '''
        :type client: RestInstaller
        '''
        user = self.SSH.getInstallerUserID(client.email)
        if not user:
            self.AddMessage('Register user %s' % client.email)
            response = client.register()
            self.AssertTrue(response['status'], 'Response status False', 'Response status True')
            code = self.getInstalleEmailCode(client.email)
            self.AddMessage('Complete register user')
            response = client.complete_register(code)
            self.AssertResponseCode(response, 200)
            self.AssertLoginWasSuccess(usr_email='admin@tycomonitor.com', usr_password='Admin123')
            whoami = self.GuiApi.Login.whoami()
            self.AssertTrue(whoami, 'Not OK', 'OK')
            self.change_installer_status(email=self.data.installer_email, action='accept')
            self.AddMessage('Response: %s' % response.json())
            self.AddMessage('Set password for user')
            response = client.setPassword()
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
        else:
            self.AddSuccess('User "%s" has already registered' % client.email)

    def check_installer_status_on_web(self, email: str, status: str):
        self.AddMessage(f'Checking that installer {email} status is {status}')
        response = self.GuiApi.Installers.installers_list()
        self.CheckResponseCodeStatusSuccess(response)
        installers = response.json()['data']['rows']
        for i in installers:
            if i['email'] == email:
                message = f"Status is {i['status']}"
                self.ExpectTrue(i['status'] == status, message, message)

    def change_installer_status(self, email: str, action: str):
        actions = {
            'accept': self.GuiApi.Installers.accept_installer,
            'reject': self.GuiApi.Installers.reject_installer
        }
        self.AddMessage(f'Change installer {email} status to {action}')
        installer_id = self.GuiApi.Installers.getInstallerId(email)
        response = actions.get(action)(installer_id=installer_id)
        self.CheckResponseCodeStatusSuccess(response)

    def check_user_status_on_web(self, email: str, status: str):
        self.AddMessage('Checking that user {} status is {}'.format(email, status))
        response = self.GuiApi.InteractiveUsers.get_all()
        self.CheckResponseCodeStatusSuccess(response)
        users = response.json()['data']['rows']
        for u in users:
            if u['pru_email'] == email:
                message = 'Status is {}'.format(u['pru_status'])
                self.ExpectTrue(u['pru_status'] == status, message, message)

    def getInstalleEmailCode(self, email):

        self.SSH._sshopen()
        result = self.SSH._sshrun_command("mysql power-installer -nBe \"SELECT email_code from installers where email='{}'\"".format(email)).replace('\n', '').replace('email_code', '')
        self.SSH.close()
        return result


@executable(context=Data)
class RemoveInstallerRestUser(TestCase):
    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(RemoveInstallerRestUser, self).__init__(*args, **kwargs)

    def RemoveUsers_Test(self):
        self.AddMessage("Start")
        self.SSH.removeInstallerUser(email=self.data.installer_email)
        self.SSH.removeInteractiveUser(email=self.data.power_user)
        self.AddMessage("Remove users complited")