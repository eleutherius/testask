# from ..library import TestCase
from ..library.common import DscMethod
from testcase.testflow import executable
from atl.utils.sequences import Namespace
from ipmp.pages import GuiApi
import json
from threading import Thread
from atl.utils.sequences import Namespace
from ipmp.emu.neo import NeoPanel
import time

_ALIAS_ = 'MyPanelsTests'


class Data(Namespace):

    def __init__(self):
        super(Data, self).__init__()
        self.psp_panel_id: str
        self.device_number = 1
        self.psp_panel_serial = "C10070010101"
        self.psp_fibro_account = "6999999999"
        self.psp_system_account = "654321"


"""
1. Enrol panel with contact -> activate -> check contact present on gui
2. Enrol panel -> activate -> generate two same events -> check that both events are displayed
3. Enrol panel (GSM) -> activate -> send hb -> disconnect panel -> check state status for gprs
"""


@executable(context=Data)
class TestTask3_1(DscMethod):

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask3_1, self).__init__(*args, **kwargs)
        self.neo = NeoPanel(self.data.psp_panel_serial, self.data.psp_fibro_account, 'IP', model='HS3128')
        self.neo.config.host = self.connection.hostname

    def Setup(self):
        self.AssertLoginWasSuccess()

    def Close(self):
        serials = [self.neo.serial]
        self.AssertPanelWasRemovedIfNeeded(serials)

    def EnrollPanel_Test(self):
        self.neo.add_device("contact", self.data.device_number)
        self.enroll_panel()
        get_zone = self.get_device(self.data.psp_panel_serial, "ZONE", self.data.device_number)
        self.AssertTrue(get_zone["subtype"] == "CONTACT", "Zone is not contact", f"Zone {self.data.device_number} is "
                                                                                 f"contact")

    def get_device(self, serial, device_type: str, device_number: int) -> dict:
        unt_id = self.GuiApi.Units.getUnitId(serial)
        return self.GuiApi.Diagnostic.getDevice(unt_id, device_type, device_number)

    def EnrollPspGPRS_Panel_Test(self):
        self.neo.setMedia("GSM")
        self.enroll_panel()
        self.AssertTrue(self.getStatusGsmUnit(self.neo.serial), "GSM module is not exist!", "GSM  module is exist")

    def enroll_panel(self):
        thread = Thread(target=self.neo.connectITv2)
        thread.start()
        self.activate_neo_panel(panel=self.neo)
        self.neo.sendInit()
        self.neo.sendHeartBeat()
        self.neo.config.version = ''
        self.neo.stopITv2Session()
        thread.join()

    def GenerateEvents_Panel_Test(self):
        self.enroll_panel()
        self.GenerateAlarm(self.neo, alarm='PA')
        self.GenerateAlarm(self.neo, alarm='PA')
        # events = self.GuiApi.Events.getEvents()
        time.sleep(3)
        events_id = self.getIdEventsForPanel(self.neo.serial)
        self.AssertTrue(len(events_id) == 2, "Events are not displayed",  "Events are displayed")
