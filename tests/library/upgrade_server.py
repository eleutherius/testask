import os

from requests import request
from threading import Thread
import time

from atl.utils.stopwatch import StopWatch
from ipmp.emu.upgrade_server.upgrade_server import app
from tests.library.common import DscMethod
from ipmp.setup import getLocalIP, getFreePort


class UpgradeServer(DscMethod):

    def __init__(self, *args, **kwargs):
        super(UpgradeServer, self).__init__(*args, **kwargs)
        self.server_upgrade_ip = getLocalIP(self.connection.hostname, 8080)
        self.server_upgrade_port = getFreePort()
        self.server = None

    def add_repository_root_ca(self):
        self.AddMessage('Add root CA')
        self.SSH._sshopen()
        cmd = 'cp /opt/visonic/ipmp/share/RepositoryRootCA.cert.pem /etc/pki/ca-trust/source/anchors/'
        self.SSH._sshrun_command(cmd)
        cmd = 'update-ca-trust'
        self.SSH._sshrun_command(cmd)
        self.SSH.close()

    def check_connection(self, ip: str, port: str):
        self.AddMessage('Check connection ip %s port %s' % (ip, port))
        self.SSH._sshopen()
        cmd = 'nc -vz %s %s' % (ip, port)
        result = self.SSH._sshrun_command(cmd)
        self.AddMessage(result)
        self.SSH.close()

    def run_upgrade_server(self):
        self.add_repository_root_ca()
        key = os.path.abspath(os.path.join(os.path.dirname(__file__), 'neo-repo-test.visonic.key.pem'))
        pem = os.path.abspath(os.path.join(os.path.dirname(__file__), 'neo-repo-test.visonic-chained.cert.pem'))
        self.AddMessage('Config upgrade server ip - %s port %d' % (self.server_upgrade_ip, self.server_upgrade_port))
        self.server = Thread(target=app.run, kwargs={'host': self.server_upgrade_ip, 'port': self.server_upgrade_port, 'debug': True,
                             'use_reloader': False, "ssl_context": (pem, key)})
        self.AddMessage('Start upgrade server')
        self.server.start()

    def stop_upgrade_server(self):
        self.AddMessage('Stop upgrade server')
        response = request('post', 'https://%s:%d/shutdown' % (self.server_upgrade_ip, self.server_upgrade_port), verify=False)
        self.ExpectResponseCode(response, 200)
        self.server.join()

    def wait_sync_with_upgrade_server(self, timeout: int = 190):
        sync = False
        self.AddMessage('Wait sync with upgrade server')
        for _ in StopWatch(timeout, 10):
            response = request('get', 'https://%s:%d/sync' % (self.server_upgrade_ip, self.server_upgrade_port), verify=False)
            self.ExpectResponseCode(response, 200)
            if response.json()['sync_status']:
                sync = True
                self.AddSuccess('Sync is successful')
                break
            self.AddMessage('Sync is False')
        self.AssertTrue(sync, 'Sync is failed')

    def add_package(self, package: list):
        self.AddMessage('Add package')
        response = request('post', 'https://%s:%d/Firmware/Add' % (self.server_upgrade_ip, self.server_upgrade_port),
                           json=package, verify=False)
        self.ExpectResponseCode(response, 200)

    def set_sync_status(self, status: bool):
        self.AddMessage('Set sync status %s' % str(status))
        status = {'sync': status}
        response = request('post', 'https://%s:%d/sync/set' % (self.server_upgrade_ip, self.server_upgrade_port),
                           json=status, verify=False)
        self.ExpectResponseCode(response, 200)

    def sendRequest(self, mac, url, **data):
        self.AddMessage('SW Upgrader: request to server: URL - %s, data %s' % (url, data))
        data['mac'] = mac
        response = request('post', url, verify=False, json=data)
        self.ExpectResponseCode(response, 200)

    def sendRequestWithTimeout(self, mac, url, **data):
        self.sendRequest(mac, url, **data)
        time.sleep(30)

    def send_stage(self, mac: str, code: str):
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/PanelStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), code=code)

    def start_rsu(self, mac: str):
        # start
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/PanelStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), code='C1')
        # download
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/SessionStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), percent=0)
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/SessionStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), percent=50)
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/SessionStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), percent=100)
        # ready
        self.sendRequest(mac, "https://%s:%d/Control/PanelStage" % (self.server_upgrade_ip, self.server_upgrade_port),
                         code='C0')
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/FileStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), code='AB')
        # begin
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/PanelStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), code='C2')
        # finished
        self.sendRequestWithTimeout(mac, "https://%s:%d/Control/PanelStage" % (
        self.server_upgrade_ip, self.server_upgrade_port), code='A0')

    def start_mass_rsu(self, mac: list):
        self.AddMessage('Start muss upgrade')
        threads = dict()

        for serial in mac:
            threads[serial] = Thread(target=self.start_rsu, kwargs={'mac': serial})
            threads[serial].start()

        for _ in StopWatch(300, 1):
            if not threads:
                break
            for serial, thread in threads.copy().items():
                if not thread.is_alive():
                    thread.join()
                    threads.pop(serial)
        self.AddMessage('End muss upgrade')

