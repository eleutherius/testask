from ipmp.emu.neo import NeoPanel
from ipmp.emu.pmax.pmax_client import PmaxPanel
from threading import Thread
import time

class PanelInterface(object):

    def ConnectPanel(self):
        raise NotImplementedError

    def DisconnectPanel(self, thread):
        raise NotImplementedError

    def add_device(self, dev_name, dev_number, preenrolled=None):
        raise NotImplementedError

    def setUserCode(self, user, code):
        raise NotImplementedError

    def remove_device(self, device, number):
        raise NotImplementedError

    def set_device_flag(self, flag_name, value, dev_num, dev_type):
        raise NotImplementedError

    def setUserPartition(self, user, partition):
        # for neo partition = partition mask
        raise NotImplementedError

    def getUserCode(self, user):
        raise NotImplementedError

    def setMedia(self, media):
        raise NotImplementedError

    def cleanLog(self):
        raise NotImplementedError

    def set_zone_activation(self, number, activation_type, timestamp):
        raise NotImplementedError

    def appendLogEvent(self, id, dev_num, partition, time=None, dev_type=None):
        raise NotImplementedError

class NeoPanelInterface(PanelInterface):

    def __init__(self, serial, account, logger, media, hostname, model='HS2128E', activate=None):
        self.panel = NeoPanel(serial=serial, account=account, logger=logger, media=media, model=model)
        self.panel.config.host = hostname
        self.activation = activate

    def ConnectPanel(self):
        itv2_thread = Thread(target=self.panel.connectITv2)
        itv2_thread.start()
        time.sleep(3)
        self.activation
        return itv2_thread

    def DisconnectPanel(self, thread):
        self.panel.core.itHandler.finish_session = True
        thread.join()

    def add_device(self, dev_name, dev_number, preenrolled=None):
        self.panel.add_device(name=dev_name, number=dev_number)

    def setUserCode(self, user, code):
        self.panel.setUserCode(user=user, code=code)

    def remove_device(self, device, number):
        self.panel.remove_device(device, number)

    def set_device_flag(self, flag_name, value, dev_num, dev_type):
        self.panel.set_device_flag(flag=flag_name, value=value, dev_number=dev_num, dev_type=dev_type)

    def setUserPartition(self, user, partition=128):
        self.panel.setUserPartition(user, partition)

    def getUserCode(self, user):
        code = self.panel.getUserCode(user)
        return code

    def setMedia(self, media):
        self.panel.setMedia(media=media)

    def cleanLog(self):
        self.panel.cleanLog()

    def set_zone_activation(self, number, activation_type, timestamp):
        self.panel.set_zone_activation(number=number, activation_type=activation_type, timestamp=timestamp)

    def appendLogEvent(self, id, dev_num, partition, time=None, dev_type=None):
        self.panel.appendLogEvent(code=id, timestamp=time, appointment=dev_num, partition=partition)

class PmaxPanelInterface(PanelInterface):

    def __init__(self, serial, account, logger, media, hostname, activate=None):
        self.panel = PmaxPanel(serial=serial, account=account, logger=logger)
        self.panel.config.host = hostname
        self.panel.config.media = media

    def ConnectPanel(self):
        self.panel.config.keep_session = True
        wakeup = Thread(target=self.panel.wake_up, kwargs={'forced': True})
        wakeup.start()
        return wakeup

    def DisconnectPanel(self, thread):
        self.panel.config.keep_session = False
        thread.join()

    def add_device(self, dev_name, dev_number, preenrolled=None):
        self.panel.add_device(dev_name=dev_name, dev_num=dev_number, preenrolled=preenrolled)

    def setUserCode(self, user, code):
        self.panel.setUserCode(user=user, code=code)

    def remove_device(self, device, number):
        self.panel.remove_device(device, number)

    def set_device_flag(self, flag_name, value, dev_num, dev_type):
        self.panel.set_device_flag(name=flag_name, value=value, num=dev_num, type=dev_type)

    def setUserPartition(self, user, partition):
        self.panel.setUserPartition(user, partition)

    def getUserCode(self, user):
        code = self.panel.getUserCode(user)
        return code

    def setMedia(self, media):
        self.panel.config.media = media

    def cleanLog(self):
        self.panel.cleanLog()

    def set_zone_activation(self, number, activation_type, timestamp):
        self.panel.set_zone_activation(number=number, activation_type=activation_type, timestamp=timestamp)

    def appendLogEvent(self, id, dev_num, partition, time=None, dev_type=None):
        self.panel.appendLogEvent(pnet_id=id, dev_type=dev_type, dev_num=dev_num, partition=partition, time=time)
