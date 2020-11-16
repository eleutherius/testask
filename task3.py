"""
1. Create a group, add two panels (pmax, neo), choose new group for neo panel.
2. Choose a different sms broker for wakeup and notifications.
3. Register rest client and installer complete registration ,  delete these users.
"""

from ipmp.pages import GuiApi

class Rutiner():
    def __init__(self, host:str, email:str, passwd:str):
        self.host: str = host
        self.email: str = email
        self.passwd: str = passwd
        self.gui_api = GuiApi(self.host)

    def create_group(self, name):
        self.gui_api.Login.login(usr_email=self.email, usr_password=self.passwd)
        resp = self.gui_api.Group.addGroup(name)
        return {name: resp.json()['data']['utg_id']}
    def add_panels(self):
        self.gui_api.Login.login(usr_email=self.email, usr_password=self.passwd)
        # self.gui_api.Units.add()
        resp = self.gui_api.Units.add(unt_serial="A3B1B3", unt_account="005678", unt_name="03B1B3",
                                      _unt_module_gprs=True, _unt_module_bba=False, utg_id=int("1"), vendor='POWER_MASTER')
        print (resp.json()['Response'])

        resp = self.gui_api.Units.add(unt_serial="C10070010101", unt_account="7541FF",
                                      unt_name="000070010101", utg_id=int("1"), vendor='NEO',
                                      _unt_module_gprs='offline',
                                      _unt_module_bb='offline')

from ipmp.setup import IpmpInitalSetup
from ipmp.emu.neo import NeoPanel
from ipmp.emu.pmax import PmaxPanel

rutine  = Rutiner("94.125.123.58", "admin@tycomonitor.com", "Admin123")
rutine.add_panels()
