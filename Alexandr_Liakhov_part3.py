"""
1. Заенролить на ПМ эмулятор со всеми девайсами.
2. На одном девайсе сгенерить ивент.
3. На каком-то сгенерить трабл.
4. Проверить это с момощью REST API
5. *Проверить Walk test
"""
from builtins import list

from ipmp.emu.neo import NeoPanel
from collections import OrderedDict
import time
import sys
import logging
from ipmp.pages.rest.api import GuiApi
import gevent
from ipmp.emu.neo.devdb import DeviceType
import logging
import random
import threading


def random_serial():
    List = ["A", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    random.shuffle(List)
    _serial = ''.join([random.choice(List) for x in range(12)])
    return _serial


IP = "192.168.99.246"
serial = random_serial()


def add_dsc_panel():
    panel = NeoPanel(serial=serial, account=serial, media='IP', model='HS3128',
                     logger=logging.basicConfig(level='DEBUG'))
    panel.config.host = IP
    for i in DeviceType:
        panel.config.devices.add_device(i)
    panel.set_device_trouble("tamper", 1, 2)
    panel.set_device_alarm("burglar", 1, 1)

    def stop_itv2():
        time.sleep(30)
        panel.stopITv2Session()

    thread_ac = threading.Thread(target=stop_itv2)
    thread_ac.start()

    panel.connectITv2()


# add_dsc_panel()


def check_for_warnings(panel_serial: str, zone_number: int):
    logger = logging.getLogger('test')
    logger.setLevel('DEBUG')
    logger.addHandler(logging.StreamHandler())
    api = GuiApi(IP, logger)
    api.Login.login(usr_email='admin@tycomonitor.com', usr_password='Admin123')

    unit_id = api.Units.getUnitId(panel_serial)
    dev_id = api.Diagnostic.getDeviceId(unit_id, 'ZONE', zone_number)
    all_info = api.Diagnostic.getDevices(unit_id)
    for i in all_info:
        if i.get('id', '') == dev_id:
            if i.get('warnings', ''):
                for var1 in i.get('warnings', ''):
                    print(f"We have warnings type: {var1.get('type', '')} severity: {var1.get('severity', '')}")


# check_for_warnings(serial, 1)
# check_for_warnings(serial, 2)


def walk_test(panel_serial):
    logger = logging.getLogger('test')
    logger.setLevel('DEBUG')
    logger.addHandler(logging.StreamHandler())
    api = GuiApi(IP, logger)
    api.Login.login(usr_email='admin@tycomonitor.com', usr_password='Admin123')
    unit_id = api.Units.getUnitId(panel_serial)

    api.Diagnostic.post('/unit_diagnostic/walkteststart', {"unt_id": unit_id})



def add_dsc_panel2():
    panel = NeoPanel(serial=serial, account=serial, media='IP', model='HS3128',
                     logger=logging.basicConfig(level='DEBUG'))
    panel.config.host = IP

    panel.config.devices.add_device("CONTACT")
    panel.config.devices.add_device("CONTACT")

    # panel.set_device_trouble("tamper", 1, 2)
    # panel.set_device_alarm("burglar", 1, 1)

    def stop_itv2():
        time.sleep(30)
        panel.stopITv2Session()



    thread_ac = threading.Thread(target=stop_itv2)
    thread_ac.start()

    panel.connectITv2()

    logger = logging.getLogger('test')
    logger.setLevel('DEBUG')
    logger.addHandler(logging.StreamHandler())
    api = GuiApi(IP, logger)
    api.Login.login(usr_email='admin@tycomonitor.com', usr_password='Admin123')
    unit_id = api.Units.getUnitId(serial)

    dev_id = api.Diagnostic.getDeviceId(unit_id, 'ZONE', 1)
    panel.set_device_flag('open', "CONTACT", str(dev_id), 1)

    # def set_device_flag(self, flag, value, dev_type, dev_number):
    #     '''
    #     Set device attribute
    #     :param flag: Name of attribute. See .device.Device constructor
    #     :param value: Attribute value
    #     :param dev_type: type of device. See .devdb.DeviceDB constructor registerDeviceClass method calls
    #     :param dev_number: number of device
    #     :return: True or False
    #     '''

    thread_ac.start()
    panel.connectITv2()



    thread_ac.start()
    panel.connectITv2()

add_dsc_panel2()
