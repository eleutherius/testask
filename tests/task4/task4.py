from ..library import TestCase
from testcase.testflow import executable
from atl.utils.sequences import Namespace
from ipmp.pages import GuiApi
import json
from threading import Thread
from atl.utils.sequences import Namespace
from ipmp.emu.neo import NeoPanel

_ALIAS_ = 'MyPanelsTests'


class Data(Namespace):

    def __init__(self):
        self.group_name = "New group"
        self.group_id: str
        self.psp_panel_id: str

        pass


"""
1. Enrol panel with contact -> activate -> check contact present on gui
2. Enrol panel -> activate -> generate two same events -> check that both events are displayed
3. Enrol panel (GSM) -> activate -> send hb -> disconnect panel -> check state status for gprs
"""


@executable(context=Data)
class TestTask3_1(TestCase):

    def __init__(self, data, *args, **kwargs):
        self.data = data
        super(TestTask3_1, self).__init__(*args, **kwargs)

    def EnrollPanel_Test(self):
        self.AddMessage(f'Start test!')
        neo = NeoPanel('A78899999999', '6999999999', 'IP', model='HS3128')
        neo.config.version = '05.30'
        neo.config.host = self.connection.hostname
        for i in range(4):
            neo.config.fibroReceivers[i]['host'] = '0.0.0.0'
            neo.config.fibroReceivers[i]['hb'] = 0
        neo.config.Eprom.refresh()
        neo.add_device("contact", 1)
        
        thread = Thread(target=neo.connectITv2(connection_type="ip"))
        thread.start()
        thread.join()
        self.AddMessage(f'Test finish!')
