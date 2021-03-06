from ..library.common import DscMethod
from testcase.testflow import executable
from threading import Thread
from atl.utils.sequences import Namespace
from ipmp.emu.neo import NeoPanel

_ALIAS_ = 'MyPanelsTests'


class Data(Namespace):

    def __init__(self):
        super(Data, self).__init__()
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
class TestTask3(DscMethod):

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask3, self).__init__(*args, **kwargs)
        self.neo = NeoPanel(self.data.psp_panel_serial, self.data.psp_fibro_account, 'IP', model='HS3128')
        self.neo.config.host = self.connection.hostname

    def Setup(self):
        self.AssertLoginWasSuccess()

    def Close(self):
        serials = [self.neo.serial]
        self.AssertPanelWasRemovedIfNeeded(serials)

    def EnrollPanel_with_ZONE1_Test(self):
        self.neo.add_device("contact", self.data.device_number)
        self.enroll_panel()
        get_zone = self.get_device(self.data.psp_panel_serial, "ZONE", self.data.device_number)
        self.AssertTrue(get_zone["subtype"] == "CONTACT", "Zone is not contact", f"Zone {self.data.device_number} is "
                                                                                 f"contact")

    def EnrollPspPanel_via_GSM_Test(self):
        self.neo.setMedia("GSM")
        self.enroll_panel()
        self.AssertTrue(self.getStatusGsmUnit(self.neo.serial), "GSM module is not exist!", "GSM  module is exists")

    def GenerateTwoEvents_PSP_Test(self):
        self.enroll_panel()
        self.GenerateAlarm(self.neo, alarm='PA')
        self.GenerateAlarm(self.neo, alarm='PA')
        events_id = self.getIdEventsForPanel(self.neo.serial)
        self.AssertTrue(len(events_id) == 2, "Events are not displayed", "Events are displayed")

    def enroll_panel(self):
        thread = Thread(target=self.neo.connectITv2)
        thread.start()
        self.activate_neo_panel(panel=self.neo)
        self.neo.sendInit()
        self.neo.sendHeartBeat()
        self.neo.config.version = ''
        self.neo.stopITv2Session()
        thread.join()

    def get_device(self, serial, device_type: str, device_number: int) -> dict:
        unt_id = self.GuiApi.Units.getUnitId(serial)
        return self.GuiApi.Diagnostic.getDevice(unt_id, device_type, device_number)
