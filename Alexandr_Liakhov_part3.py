"""
1. Заенролить на ПМ эмулятор со всеми девайсами.
2. На одном девайсе сгенерить ивент.
3. На каком-то сгенерить трабл.
4. Проверить это с момощью REST API
5. *Проверить Walk test
"""
from ipmp.emu.neo import NeoPanel
from collections import OrderedDict
import time
import sys
import logging
from ipmp.pages.rest.api import GuiApi
import gevent
from ipmp.emu.neo.devdb import DeviceType
# from ipmp.emu.neo.devdb import DeviceNames
DeviceTypeNumbers = OrderedDict([(i, j) for j, i in list(DeviceType.items())])
print (DeviceTypeNumbers)
# IP = "94.125.123.59"
# serial = "B00000000002"
# detector = "CONTACT"
#
# panel = NeoPanel(serial=serial, account=serial, media='IP', model='HS3128')
# tasks = list()
# panel.config.host = IP
# panel.config.devices.add_device(detector)
#
# tasks.append(gevent.spawn(panel.connectITv2))
#             # time.sleep(1)
# panel.sendInit()
# panel.sendHeartBeat()
# gevent.joinall(tasks)








# from gevent.monkey import patch_all
#
# patch_all()
# from ipmp.emu.neo import NeoPanel
# import gevent
# import time
# import sys
# import typing
# import logging
# from ipmp.pages.rest.api import GuiApi


#
# class CreatorScript:
#
#     def __init__(self, ip='94.125.123.180'):
#         self.ip = ip
#
#     def _neo_panels(self, number: int):
#         serials = ['%X' % (i + 0xB00000000000) for i in range(number)]
#         panels = [NeoPanel(serial=serial, account=serial[2:], media='IP', model='HS3128') for serial in serials]
#         host = self.ip
#         tasks = list()
#         for i, panel in enumerate(panels):
#             panel.config.host = host
#             tasks.append(gevent.spawn(panel.connectITv2))
#             # time.sleep(1)
#             panel.sendInit()
#             panel.sendHeartBeat()
#         gevent.joinall(tasks)
#
#     def AddUsers(self, number):
#         logger = logging.getLogger('test')
#         logger.setLevel('DEBUG')
#         logger.addHandler(logging.StreamHandler())
#
#         for n in range(1, number):
#             api = GuiApi(self.ip, logger)
#             api.Login.login(usr_email='admin@tycomonitor.com', usr_password='Admin123')
#             api.User.add_user(usr_name="USER" + str(n), usr_email="myfavoritenumber" + str(n) + "@mail.com",
#                               usr_phone='666666' + str(n),
#                               coy_id=n, roe_id=2, usr_password="123456")
#
#             api.Login.login(usr_email="myfavoritenumber" + str(n) + "@mail.com", usr_password='123456')
#             api.User.add_user(usr_name="USERAS" + str(n), usr_email="thisnumber" + str(n) + "@mail.com",
#                               usr_phone='6336' + str(n),
#                               coy_id=n, roe_id=2, usr_password="123456")
#         #   api.Roles.add_role(roe_name='Role'+str(n*100),roe_roe_id=2,utg_id=[n])
#
#     def AddCS(self, number):
#         logger = logging.getLogger('test')
#         logger.setLevel('DEBUG')
#         logger.addHandler(logging.StreamHandler())
#
#         # CREATE 10 CS (10 unique value of Central station names,protocols,hosts,ports)
#
#         for n in range(1, number):
#             api = GuiApi(self.ip, logger)
#             api.Login.login(usr_email='admin@tycomonitor.com', usr_password='Admin123')
#             api.CentralStations.add_cs(cls_name="AStation" + str(n), cls_heart_beat=25, cls_retry_time=10,
#                                        cls_retry_count=4, hpa_host="94.125.124.1" + str(n), hpa_port=5000 + n,
#                                        cls_ssl="none",
#                                        cls_receiver=33, cls_line=2, csp_id=n)
#
#     def AddRoles(self, number):
#         logger = logging.getLogger('test')
#         logger.setLevel('DEBUG')
#         logger.addHandler(logging.StreamHandler())
#
#         for n in range(1, number):
#             api = GuiApi(self.ip, logger)
#             api.Login.login(usr_email='admin@tycomonitor.com', usr_password='Admin123')
#
#             api.Roles.add_role(roe_name='Role' + str(n), roe_roe_id=2, utg_id=[1])
