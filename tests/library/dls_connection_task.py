import threading
import time

from ipmp.emu.neo import NeoPanel


class DlsConnectionTask(threading.Thread):

    def __init__(self, neo: 'NeoPanel', dls_cmd_interrupt=b'', delay=0):
        super(DlsConnectionTask, self).__init__()
        self.delay = delay
        self.neo = neo
        self.stopped = False
        self.dls_cmd_interrupt = dls_cmd_interrupt
        self.last_finished_session = time.time()

    def stopTask(self):
        self.stopped = True

    def run(self):
        while not self.stopped:
            time.sleep(0.1)
            isDlsNeeded = self.neo.isDlsNeeded()
            self.neo.logger.debug('Need connection via Dls: %s' % isDlsNeeded)
            if isDlsNeeded:
                time.sleep(0.1)
                self.neo.connectDls(dls_cmd_interrupt=self.dls_cmd_interrupt, delay=self.delay)
                self.last_finished_session = time.time()