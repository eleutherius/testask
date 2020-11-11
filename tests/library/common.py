import os
import random
import string
import time
from datetime import datetime

from websocket import WebSocket

from .pdf_parser import PDFReportParser

try:
    from easysnmp import Session
except ModuleNotFoundError:
    pass

from ipmp.interactive.rest.client import RestAPIClient, RestInstaller
from .testunits import TestCase
from threading import Thread
from atl.utils.stopwatch import StopWatch
from ipmp.emu.pmax.pmax_client.info_data import DeviceNames as devdbDeviceNames
from ipmp.emu.neo import NeoPanel
from ipmp.emu.pmax import PmaxPanel
from ipmp.emu.dual_path import DualPathCommunicator
from ipmp.emu.neo.info_data import DeviceNames, DeviceType
from ipmp.emu.neo.models import MODELS
from ipmp.setup import SQLUtils
from .discovery_stages import (all_neo_discovery_stages, free_neo_discovery_stages, all_psp_discovery_stages,
                               free_psp_discovery_stages)
from .dls_connection_task import DlsConnectionTask


class SqlMethod(TestCase):

    def getCodeLengthFromUnitAttribute(self, serial: str) -> int:
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        # iua_id = 51 - ACCESS_CODE_LENGTH
        cmd = 'SELECT uta_value FROM unit_attribute WHERE unt_id=%s AND iua_id=51;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return int(result)

    def getInfoPanelInPmaxStateTable(self, serial: str):
        headers = ['unt_id',
                   'pxs_partition_id',
                   'pxs_state',
                   'prs_id',
                   'pxs_instant',
                   'pxs_latchkey',
                   'pxs_ready',
                   'pxs_active',
                   'psi_id',
                   'pxs_exit_delay_value',
                   'pxs_quick_exit',
                   'pxs_label']
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT ps.* FROM  pmax_state as ps WHERE unt_id=%s;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getExitDelayValueFromPmaxState(self, serial: str, partition: int) -> int:
        data = self.getInfoPanelInPmaxStateTable(serial)
        for par in data:
            if int(par['pxs_partition_id']) == partition:
                return int(par['pxs_exit_delay_value'])
        return False

    def getPartitionStateFromPmaxState(self, serial: str, partition: int) -> str:
        data = self.getInfoPanelInPmaxStateTable(serial)
        for par in data:
            if int(par['pxs_partition_id']) == partition:
                return par['pxs_state'].strip()

    def getPartitionStatesFromPmaxState(self, serial: str, partition: int) -> str:
        data = self.getInfoPanelInPmaxStateTable(serial)
        for par in data:
            if int(par['pxs_partition_id']) == partition:
                self.SSH._sshopen()
                cmd = 'SELECT psi_name FROM  panel_states_info WHERE psi_id=%s;' % par['psi_id']
                result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
                self.SSH.close()
                if not result:
                    self.SSH.logger.error('No answer from server')
                    return False
                return result.strip()

    def getQuantityPartiionInPmaxState(self, serial: str):
        return len(self.getInfoPanelInPmaxStateTable(serial))

    def checkExitDelayForPartititon(self, serial: str, partition: int, exit_delay: int):
        current_partition = None
        for part in self.getInfoPanelInPmaxStateTable(serial):
            if part['pxs_partition_id'] == str(partition):
                current_partition = part
        if current_partition:
            self.AssertTrue(current_partition['pxs_exit_delay_value'] == str(exit_delay),
                            'pxs_exit_delay_value for %s partition is not %s' % (partition, exit_delay),
                            'pxs_exit_delay_value for %s partition is %s' % (partition, exit_delay))
        else:
            self.AddFailure('Partition %s not found' % partition)

    def CheckTroubleForPanelInDB(self, serial: str, trouble: str, timeout: int = 5, wait: bool = False):
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT COUNT(*) FROM  warning WHERE unt_id=%s AND iow_id=\'%s\';' % (unit_id, trouble)
        if not wait:
            count = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        else:
            for _ in StopWatch(timeout, 1):
                count = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
                if int(count.replace('\n', '')): break
        self.SSH.close()
        if not count:
            self.SSH.logger.error('No answer from server')
            return False
        return int(count.replace('\n', ''))


    def getWarning(self, serial):
        headers = [
            'wag_id',
            'unt_id',
            'utz_id',
            'evt_id',
            'wag_changed_timestamp',
            'wag_partitions',
            'wag_in_memory',
            'iow_id'
        ]
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT w.* FROM  warning as w WHERE unt_id=%s;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return []
        return SQLUtils.parse_table(result, headers)

    def getUnitFibroAccount(self, serial: str):
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT utn_fibro_account FROM  unit_neo WHERE unt_id=%s;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return result.replace('\n', '')

    def CheckUnitAttribute(self, serial: str, attribute_name: str, attribute_value: str):
        all_attributes = self.SSH.GetUnitAttributes(serial)
        found_attribute = False
        for attr in all_attributes:
            if attr['attribute_name'] == attribute_name:
                found_attribute = True
                self.AssertTrue(attr['value'] == attribute_value, '%s attribute value is not %s' % (attribute_name,
                                                                                                    attribute_value),
                                '%s attribute value is %s' % (attribute_name, attribute_value))
        self.AssertTrue(found_attribute, 'Attribute %s not found' % attribute_name)

    def CheckUnitAttributeIsNotNull(self, serial: str, attribute_name: str,):
        all_attributes = self.SSH.GetUnitAttributes(serial)
        found_attribute = False
        for attr in all_attributes:
            if attr['attribute_name'] == attribute_name:
                found_attribute = True
                self.AssertTrue(attr['value'] != "NULL", '%s attribute value is NULL' % attribute_name,
                                '%s attribute value is %s' % (attribute_name, attr['value']))
        self.AssertTrue(found_attribute, 'Attribute %s not found' % attribute_name)

    def getInfoFromUnitZone(self, serial: str):
        headers = ['device_type', 'label', 'state_soak', 'enroll_id', 'bypass_enabled', 'state_bypass', 'rarely_used',
                   'partition', 'version', 'utz_changed_timestamp', 'utz_state_open']
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT ud.utd_name, utz_label, utz_state_soak, utz_enroll_id,  utz_bypass_enabled, utz_state_bypass, ' \
              'utz_rarely_used, utz_partitions, utz_firmware_version , utz_changed_timestamp, utz_state_open' \
              ' FROM  unit_zone INNER JOIN unit_device as ud USING(utd_id) WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getStatusGsmUnit(self, serial: str) -> str:
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = "SELECT iztg.iztg_name FROM unit_zone_type_gsm INNER JOIN info_zone_type_gsm as iztg USING(iztg_id) " \
              "WHERE utz_id=(SELECT utz_id FROM unit_zone INNER JOIN unit_device as ud USING(utd_id) " \
              "WHERE ud.utd_name='GSM' AND  unit_zone.unt_id=%s)" % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return result.replace('\n', '')

    def getInfoFromUnitLanguage(self, serial: str):
        unit_id = self.SSH.GetUnitID(serial)
        headers = [ 'unt_id',
                    'utl_name',
                    'utl_alphabet',
                    'utl_max_location_len']
        self.SSH._sshopen()
        cmd = 'SELECT ul.* FROM  unit_language as ul WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getInfoFromCustomHouseLocation(self, serial: str):
        unit_id = self.SSH.GetUnitID(serial)
        headers = ['unt_id',
                   'hel_id',
                   'uchl_name',
                   'uchl_editable']
        self.SSH._sshopen()
        cmd = 'SELECT uchl.* FROM  unit_custom_house_location as uchl WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def GetPanelInfoFromUnit(self, serial: str):
        unit_id = self.SSH.GetUnitID(serial)
        headers = [ 'unt_id',
                    'utg_id',
                    'usr_id',
                    'unt_serial',
                    'unt_account',
                    'unt_mac_address',
                    'unt_remote_access',
                    'unt_installer_remote_access',
                    'unt_pl_software_version',
                    'unt_pl_hardware_version',
                    'unt_software_version',
                    'unt_software_default',
                    'unt_eeprom_version',
                    'unt_hardware_version',
                    'unt_rsu_version',
                    'unt_boot_version',
                    'unt_configuration_variant',
                    # 'unt_ip_addr',
                    'unt_sim_number',
                    'unt_model',
                    'unt_contact_name',
                    'unt_contact_email',
                    'unt_contact_phone',
                    'unt_contact_address',
                    'unt_remark',
                    'unt_changed_timestamp',
                    'unt_vlm_version',
                    '_unt_trouble_changed_timestamp',
                    '_utg_name',
                    '_unt_alerts',
                    '_unt_alarms',
                    'unt_activated'
                    ]
        self.SSH._sshopen()
        cmd = 'SELECT u.* FROM  unit as u WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def GetQuantityLableInUnitZone(self, serial: str, lable: str):
        device = self.getInfoFromUnitZone(serial)
        for item in list(device):
            if lable not in item['label']:
                device.remove(item)
        return len(device)

    def getQuantityBypassDetectorUnitZone(self, serial: str):
        device = self.getInfoFromUnitZone(serial)
        for item in list(device):
            if item['state_bypass'] != 'yes':
                device.remove(item)
        return len(device)

    def getQuantityPendantsInUnitZone(self, serial: str):
        device = self.getInfoFromUnitZone(serial)
        result = []
        for item in device:
            if item['enroll_id'].startswith('320-') or item['enroll_id'].startswith('322-'):
                result.append(item)
        return len(result)

    def GetQuantityDeviceType(self, serial: str, device_type: str):
        device = self.getInfoFromUnitZone(serial)
        for item in list(device):
            if item['device_type'] != device_type:
                device.remove(item)
        return len(device)

    def CheckFirmwareVersionINUnitZone(self, serial: str, label: str):
        device = self.getInfoFromUnitZone(serial)
        for item in device:
            if label in item['label']:
                self.AssertTrue(item['version'] != 'NULL', '%s version is NULL' % item['label'],
                                '%s version is %s' % (item['label'], item['version']))

    def CheckSoftwareVersionInUnit(self, serial: str):
        version = self.GetPanelInfoFromUnit(serial)[0]['unt_software_version']
        self.AssertTrue(version != 'NULL', 'unt_software_version for panel %s in unit table is NULL' % serial,
                        'unt_software_version for panel %s in unit table is %s' % (serial, version))

    def CheckFieldUnitTable(self, serial: str, field: str, value: str):
        panel_info = self.GetPanelInfoFromUnit(serial)[0]
        self.AssertTrue(panel_info[field] == value,
                        '%s for panel %s is not %s, value is %s' % (field, serial, value, panel_info[field]),
                        '%s for panel %s is %s' % (field, serial, value))

    def GetAllUserFromPmaxUsers(self, serial):
        headers = [
            'pxu_id',
            'unt_id',
            'pxu_name',
            # 'pxu_mobile',
            'pxu_email',
            'pxu_panel_id',
            'pxu_is_admin',
            'pxu_code',
            'pxu_partitions',
            'pxu_label',
            'pxu_permissions']
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT pu.* FROM  pmax_user as pu WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getAllProccesForPanel(self, serial, unit_id=None):
        headers = [
            'prs_type',
            'prs_status',
            'prs_error_message']
        if not unit_id:
            unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT prs_type, prs_status, prs_error_message FROM process WHERE unt_id=%s;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getPartitionsForPanelFromPmaxState(self, serial: str):
        headers = [ 'unt_id',
                    'pxs_partition_id',
                    'pxs_state',
                    'prs_id',
                    'pxs_instant',
                    'pxs_latchkey',
                    'pxs_ready',
                    'pxs_active',
                    'psi_id',
                    'pxs_exit_delay_value',
                    'pxs_quick_exit',
                    'pxs_label'
                    ]
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT ps.* FROM  pmax_state as ps WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getInfFromUnitDeviceRanges(self, serial: str) -> dict:
        headers = ['utd_name',
                   'unt_id',
                   'utd_id',
                   'udr_evt_off',
                   'udr_max_dev',
                   ]
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT ud.utd_name, udr.* FROM unit_device_ranges as udr ' \
              'INNER JOIN unit_device as ud USING(utd_id) WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getInfoFromPrivateEmail(self, serial: str) -> list:
        headers = ['pee_id',
                   'pee_user_number',
                   'pee_email',
                   'unt_id',
                   'pee_etp_bitmask',
                   ]
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT pe.* FROM private_email as pe WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getInfoFromPrivateSms(self, serial: str) -> list:
        headers = ['pes_id',
                   'pes_user_number',
                   'pes_phone',
                   'unt_id',
                   'pes_etp_bitmask',
                   ]
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT ps.* FROM private_sms as ps WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def getInfoFromPrivateMms(self, serial: str) -> list:
        headers = ['pes_id',
                   'pem_user_number',
                   'pem_phone',
                   'unt_id',
                   'pem_etp_bitmask',
                   ]
        unit_id = self.SSH.GetUnitID(serial)
        self.SSH._sshopen()
        cmd = 'SELECT pm.* FROM private_mms as pm WHERE unt_id=%s ;' % unit_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)

    def checkStatusAllPartitionFroPanel(self, serial: str, status: str):
        result = self.getPartitionsForPanelFromPmaxState(serial)
        for partition in result:
            self.AssertTrue(partition['prs_id'] == status, '%s status is not %s, status is %s' %
                            (partition['pxs_label'], status, partition['prs_id']), '%s status is %s' %
                            (partition['pxs_label'], status))

    def checkAllPartitonsLableIsNotNull(self, serial: str):
        result = self.getPartitionsForPanelFromPmaxState(serial)
        for partition in result:
            self.AssertTrue(partition['pxs_label'] != 'NULL', 'Partition id %s status is NULL' % partition['pxs_partition_id'],
                            'Partition id %s label is %s' % (partition['pxs_partition_id'], partition['pxs_label']))

    def checkEnrollIdIsNotNull(self, serial: str, device_type):
        device = self.getInfoFromUnitZone(serial)
        for item in list(device):
            if item['device_type'] == device_type:
                self.AssertTrue(item['enroll_id'] != 'NULL', '%s enroll_id is NULL' % device_type,
                                '%s enroll id is %s' % (device_type, item['enroll_id']))

    def checkFieldsIsNotNullInUnitZone(self, serial: str, fields: str):
        device = self.getInfoFromUnitZone(serial)
        for item in list(device):
            self.ExpectTrue(item[fields] != 'NULL', '%s for %s is NULL' % (fields, item['device_type']),
                            '%s - %s is %s' % (item['device_type'], fields, item[fields]))

    def checkQuantityDetectoEnabledBypassDisabledAndEnabledInDB(self, serial: str, enabled, disabled):
        data = self.getInfoFromUnitZone(serial)
        bypass_enabled = []
        for item in data:
            if 'detector' in item['label']:
                bypass_enabled.append(item['bypass_enabled'])
        self.AssertTrue(enabled == bypass_enabled.count('yes'), 'Incorrect quantity detector with bypass_enabled is yes',
                        'All detector with bypass_enabled is yes present in DB(unit_zone)')
        self.AssertTrue(disabled == bypass_enabled.count('no'), 'Incorrect quantity detector with bypass_enabled is no',
                        'All detector with bypass_enabled is no present in DB(unit_zone)')

    def getUnitValueFromUnitZone(self, serial: str, label: str) -> dict:
        time.sleep(0.5)
        data = self.getInfoFromUnitZone(serial)
        result = None
        for item in data:
            if item['label'] == label:
                result = item
        return result

    def checkEditableForAllZone(self, serial: str, editable: str):
        """
        :param serial:
        :param editable: yes or no
        """
        result = self.getInfoFromCustomHouseLocation(serial)
        for item in result:
            self.ExpectTrue(item['uchl_editable'] == editable,
                            'Editable for %s is %s' % (item['uchl_name'], item['uchl_editable']),
                            'Editable for %s is %s' % (item['uchl_name'], item['uchl_editable']))

    def checkEmailForUser(self, serial: str, email: str, user: int):
        """
        :param user: 1,2,3,4
        """
        result = self.getInfoFromPrivateEmail(serial)
        self.ExpectTrue(result[user - 1]['pee_email'] == email,
                        'Incorrect saved email(%s) for user %s' % (result[user-1]['pee_email'], user),
                        'Correct email(%s) saved for user-%s' % (result[user-1]['pee_email'], user))

    def checkSmsPhoneForUser(self, serial: str, phone: str, user: int):
        """
        :param user: 1,2,3,4
        """
        result = self.getInfoFromPrivateSms(serial)
        self.ExpectTrue(result[user - 1]['pes_phone'] == phone,
                        'Incorrect saved sms phone(%s) for user %s' % (result[user - 1]['pes_phone'], user),
                        'Correct sms phone(%s) saved for user-%s' % (result[user - 1]['pes_phone'], user))

    def checkMmsPhonelForUser(self, serial: str, phone: str, user: int):
        """
        :param user: 1,2,3,4
        """
        result = self.getInfoFromPrivateMms(serial)
        self.ExpectTrue(result[user - 1]['pem_phone'] == phone,
                        'Incorrect saved mms phone(%s) for user %s' % (result[user - 1]['pem_phone'], user),
                        'Correct mms phone(%s) saved for user-%s' % (result[user - 1]['pem_phone'], user))

    def get_name_upgrade_packages(self, uep_type: str) -> list:
        self.SSH._sshopen()
        cmd = 'SELECT uep_name FROM upgrade_package WHERE uep_type=\'%s\' ;' % uep_type
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return [name for name in result.split('\n') if name]

    def check_upgrade_package(self, uep_type: str, packages: list):
        self.AddMessage('Check uodrade packages in in database -> upgrade_package')
        packages_in_db = self.get_name_upgrade_packages(uep_type)
        for package in packages:
            try:
                packages_in_db.remove(package)
            except ValueError:
                self.AssertTrue(False, 'Package - %s not present in database' % package)
        self.ExpectNotTrue(packages_in_db, 'There are other packages in the databas %s' % str(packages_in_db),
                           'All Upgrade Packages for Panel and Powerlink write to this table')

    def get_quantity_process_runner(self, batch_id: str) -> int:
        self.SSH._sshopen()
        cmd = 'select count(*) from process_runner where batch_id=\'%s\' ;' % batch_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return int(result)

    def check_unique_batch_id(self, batch_id: str):
        self.SSH._sshopen()
        cmd = 'select count(*) from process_batch where batch_id=\'%s\' ;' % batch_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        self.ExpectTrue(int(result) == 1, 'Created batch does not have unique ids', 'Created batch with unique ids')


    def get_from_process_runner(self, prs_id: int) -> dict:
        headers = ['runner_type',
                   'runner_status',
                   'unt_serial',
                   'batch_id',
                   'runner_params',
                   'runner_created_timestamp'
                   ]
        self.SSH._sshopen()
        cmd = 'select runner_type, runner_status, _unt_serial, batch_id, runner_params, runner_created_timestamp from process_runner where prs_id=\'%d\' ;' % prs_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)[0]

    def get_from_process(self, prs_id: int) -> dict:
        headers = ['unt_serial',
                   'usr_name',
                   'prs_type',
                   'prs_status',
                   'prs_created_timestamp',
                   'prs_finished_timestamp',
                   ]
        self.SSH._sshopen()
        cmd = 'select _unt_serial, _usr_name, prs_type, prs_status,  prs_created_timestamp, prs_finished_timestamp from process where prs_id=%d ;' % prs_id
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result:
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)[0]

    def check_runners_value(self, prs_id, batch_id: str, runner_status: str, runner_type: str, unt_serial: str, package: str):
        result = self.get_from_process_runner(prs_id)
        self.AddMessage(f'Check runner: {result}')
        self.AssertTrue(result, 'Not found process with batch_id - %s' % batch_id, 'Check runners value')
        self.ExpectTrue(result['runner_status'] == runner_status,
                        'Incorrect runner_status %s' % result['runner_status'], 'Correct runner_status')
        self.ExpectTrue(result['runner_type'] == runner_type, 'Incorrect runner_type %s' % result['runner_type'],
                        'Correct runner_type')
        self.ExpectTrue(result['unt_serial'] == unt_serial, 'Incorrect unt_serial %s' % result['unt_serial'],
                        'Correct unt_serial')
        self.ExpectTrue(result['batch_id'] == batch_id, 'Incorrect batch_id %s' % result['batch_id'],
                        'Correct batch_id')
        self.ExpectTrue(package in result['runner_params'],
                        'Package name not present in runners_params %s' % result['runner_params'],
                        'Package name present in runners_params')
        try:
            self.ExpectTrue(datetime.strptime(result['runner_created_timestamp'], '%Y-%m-%d %H:%M:%S') and result[
                'runner_created_timestamp'] != '0000-00-00 00:00:00',
                            'Incorrect runner_created_timestamp %s' % result['runner_created_timestamp'],
                            'Correct runner_created_timestamp')
        except ValueError:
            self.AddFailure('Incorrect runner_created_timestamp %s' % result['runner_created_timestamp'])

    def check_process_value(self, prs_id: int, unt_serial: str, prs_status: str, prs_finished_timestamp: bool,
                            prs_type: str = 'SoftwareUpgrade', usr_name: str = 'Default Super Admin'):
        result = self.get_from_process(prs_id)
        self.AssertTrue(result, 'Process %d not found' % prs_id, 'Check process value')
        self.ExpectTrue(result['unt_serial'] == unt_serial, 'Incorrect unt_serial %s' % result['unt_serial'],
                        'Correct unt_serial')
        self.ExpectTrue(result['usr_name'] == usr_name, 'Incorrect usr_name %s' % result['usr_name'],
                        'Correct usr_name')
        self.ExpectTrue(result['prs_type'] == prs_type, 'Incorrect prs_type %s' % result['prs_type'],
                        'Correct prs_type')
        self.ExpectTrue(result['prs_status'] == prs_status, 'Incorrect prs_status %s' % result['prs_status'],
                        'Correct prs_status')
        try:
            self.ExpectTrue(datetime.strptime(result['prs_created_timestamp'], '%Y-%m-%d %H:%M:%S') and result[
                'prs_created_timestamp'] != '0000-00-00 00:00:00',
                            'Incorrect prs_created_timestamp %s' % result['prs_created_timestamp'],
                            'Correct prs_created_timestamp')
        except ValueError:
            self.AddFailure('Incorrect prs_created_timestamp %s' % result['prs_created_timestamp'])

        try:
            if prs_finished_timestamp:
                self.ExpectTrue(datetime.strptime(result['prs_finished_timestamp'], '%Y-%m-%d %H:%M:%S') and result[
                    'prs_finished_timestamp'] != '0000-00-00 00:00:00',
                                'Incorrect prs_finished_timestamp %s' % result['prs_finished_timestamp'],
                                'Correct prs_finished_timestamp')
            else:
                self.ExpectTrue(datetime.strptime(result['prs_finished_timestamp'], '%Y-%m-%d %H:%M:%S') and result[
                    'prs_finished_timestamp'] == '0000-00-00 00:00:00',
                                'Incorrect prs_finished_timestamp %s' % result['prs_finished_timestamp'],
                                'Correct prs_finished_timestamp')
        except ValueError:
            self.AddFailure('Incorrect prs_finished_timestamp %s' % result['prs_finished_timestamp'])

    def get_roles_form_db(self):
        headers = ['roe_id',
                   'roe_roe_id',
                   'usr_id',
                   'roe_name',
                   'roe_creator_name',
                   'roe_readonly',
                   'roe_hidden',
                   ]
        self.SSH._sshopen()
        cmd = 'select * from role;'
        result = self.SSH._sshrun_command(self.SSH.DataBaseQuery % cmd)
        self.SSH.close()
        if not result :
            self.SSH.logger.error('No answer from server')
            return False
        return SQLUtils.parse_table(result, headers)


class CommonMethod(SqlMethod):

    def __init__(self, *args, **kwargs):
        super(CommonMethod, self).__init__(*args, **kwargs)
        self.iac = '12345678123456781234567812345678'
        # self.VISONIC_POWERMANAGE_MIB = '1.3.6.1.4.1.20649.715.80'
        self.VISONIC_POWERMANAGE_MIB = 'VISONIC-POWERMANAGE-MIB'
        self.thread = None
        self.second_thread = None
        self.thread_pmax = None
        self.snmp = None
        self.android_push_server = 'fcm.googleapis.com'
        self.ios_push_server = 'gateway.push.apple.com'
        self.orange_broker = 'comunicasms.orange.es'
        self.repo_host = '172.16.3.70'
        self.repo_user = 'auto'
        self.repo_pwd = 'visonic'
        self.repo_fqdn = 'repo-03.visonic'

    def getUntId(self):
        unt_id = self.GuiApi.Units.getUnitId(self.emu.serial_number)
        self.AssertTrue(unt_id, 'Unit "%s" was not found')
        return unt_id

    def waitReportCreated(self, name, timeout=30.00):
        ret_id = self.GuiApi.Reports.waitReportCreated(name, timeout=timeout)
        self.AssertTrue(ret_id, 'Report was not created', 'Report was created')
        return ret_id

    def downloadReport(self, report_name, report_type='pdf', save_name=None) -> PDFReportParser:
        if save_name is None: save_name = report_name
        path = os.path.join(self.logFolder, save_name + '.' + report_type)
        response = self.GuiApi.Reports.downloadReport(report_name, report_type=report_type)
        self.AssertTrue(response.status_code == 200, 'Download status code is "%s"' % response.status_code,
                        'Download status code is "%s"' % response.status_code)
        with open(path, 'wb') as f: f.write(response.content)
        parser = PDFReportParser(path, self.connection.logger)
        parser.parseReport()
        return parser

    def compareDict(self, actual, expected):
        pattern = '"%s" is "%s"'
        for key, value in expected.items():
            actual_result = actual[key]
            result = actual_result == value
            message = pattern%(key, actual_result)
            if not self.ExpectWasSuccesfull(result, message, message):
                self.AddMessage('Expected: %s'%value)

    def setupSnmp(self, user: str = 'visadm', psw: str = 'Admin123'):
        self.snmp = Session(hostname=self.connection.hostname, version=3, remote_port=161,
                            security_level='authNoPriv', security_username=user, auth_password=psw,
                            auth_protocol='SHA')
        return self.snmp

    def createRestApiClient(self, panel_serial: str, token: str = '1234', user_code: str = '1111', version: str = '8.0'):
        self.AddMessage('Create Rest Api Client version - %s, serial panel - %s' % (version, panel_serial))
        client = RestAPIClient(self.connection.hostname, token, panel_serial, user_code,
                               version=version, format='json', logger=self.connection.logger)
        client.email = self.email_client.email
        client.password = 'Password*1'
        return client

    def createInstallerClient(self, panel_serial: str, password: str = 'Password*1'):
        version = self.rest_version.installer
        self.AddMessage('Create Installer Client version - %s, serial panel - %s' % (version, panel_serial))
        client = RestInstaller(ip=self.connection.hostname, email=self.email_client.email, password=password,
                                  panel_name=panel_serial, app_id='1234', panel_code='5555', version=version, format='json', logger=self.connection.logger)
        return client

    def get_repo_credential(self):
        self.SSH._sshopen()
        self.repo_host = self.SSH._sshrun_command('cat /ha_shared/ipmp/config/repo.conf | grep IP').split('=')[1].replace('\n', '')
        self.repo_user = self.SSH._sshrun_command('cat /ha_shared/ipmp/config/repo.conf | grep LOGIN').split('=')[1].replace('\n', '')
        self.repo_pwd = self.SSH._sshrun_command('cat /ha_shared/ipmp/config/repo.conf | grep PASSWORD').split('=')[1].replace('\n', '')
        self.SSH.close()

    def sync_repo(self):
        self.AddMessage('Sync repo')
        self.SSH._sshopen()
        cmd = '/opt/visonic/ipmp/script/./vis_swupd.sh'
        self.SSH._sshrun_command(cmd)
        self.SSH.close()

    def set_repo_credential(self, repo: str = 'automation'):
        """
        :param repo: automation or default
        """
        if repo == 'default':
            host, user, pwd, fqdn = '192.168.6.6', 'ci', 'visonic', 'ci-repository2.visonic'
        else:
            host, user, pwd, fqdn = self.repo_host, self.repo_user, self.repo_pwd, self.repo_fqdn
        url = "ftp:\\/\\/{0}:{1}@{2}".format(user, pwd, host)
        self.SSH._sshopen()
        file = '/ha_shared/ipmp/config/repo.conf'
        self.SSH._setPairValue('REPO_URL', url, file)
        self.SSH._setPairValue('IP', host, file)
        self.SSH._setPairValue('LOGIN', user, file)
        self.SSH._setPairValue('PASSWORD', pwd, file)
        self.SSH._setPairValue('FQDN', fqdn, file)
        self.SSH.close()
        self.sync_repo()

    def select_email_template(self, body: str, locale: str):
        self.AddMessage('Select %s - %s template' % (body, locale))
        self.SSH._sshopen()
        file = '/ha_shared/ipmp/config/templates.conf'
        self.SSH._setPairValue('END_USER_TEMPLATES_PATH', '/ha_shared/ipmp/config/templates/%s' % body, file)
        self.SSH._setPairValue('END_USER_TEMPLATES_LOCALE', "EmailTemplateLocale(name='%s')" % locale, file)
        self.SSH.close()

    def set_upgrade_server(self, server_name: str, status_ip: str, status_port: str, download_ip: str,
                           download_port: str, upgrade_port: str, auto_authorize: str = 'no'):
        self.AddMessage('Set Software Upgrade Settings server name %s, status ip - %s, status port - %s,'
                        'download ip - %s, download port - %s , upgrade pport - %s' % (server_name, status_ip, status_port, download_ip,
                                                                  download_port, upgrade_port))
        self.SSH._sshopen()
        self.SSH._setPairValue('ITV2_UPGRADE_SERVER_NAME', server_name, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._setPairValue('ITV2_UPGRADE_SERVER_STATUS_IP', status_ip, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._setPairValue('ITV2_UPGRADE_SERVER_STATUS_PORT',status_port, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._setPairValue('ITV2_UPGRADE_SERVER_DOWNLOAD_IP', download_ip, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._setPairValue('ITV2_UPGRADE_SERVER_DOWNLOAD_PORT', download_port, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._setPairValue('ITV2_UPGRADE_SERVER_PORT', upgrade_port, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._setPairValue('ITV2_AUTO_AUTHORIZE_UPDATE', auto_authorize, '/ha_shared/ipmp/config/itv2.conf')
        self.SSH._restart_services(['neo_service'])
        self.SSH.close()

    def CheckStateStatus(self, panel: NeoPanel or PmaxPanel, chanel: str, status: str):
        panel_info = self.GetPanelInfo(panel.serial)
        self.AssertTrue(panel_info['modules'][chanel]['state'] == status, 'State for %s is %s' % (chanel,
                        panel_info['modules'][chanel]['state']), 'State for %s is %s' % (chanel, status))

    def CheckConnectedStatus(self, panel: NeoPanel or PmaxPanel, chanel: str, status: bool):
        panel_info = self.GetPanelInfo(panel.serial)
        self.AddMessage('Panel info: %s' % panel_info)
        self.AssertTrue(panel_info['modules'][chanel]['connected'] == status, 'Connected for %s is %s' % (chanel,
                        str(panel_info['modules'][chanel]['connected'])), 'Connected for %s is %s' % (chanel,
                                                                                                      str(status)))

    def CheckInstaledStatus(self, panel: NeoPanel or PmaxPanel, chanel: str, status: bool):
        panel_info = self.GetPanelInfo(panel.serial)
        self.AssertTrue(panel_info['modules'][chanel]['installed'] == status, 'Installed for %s is %s' % (chanel,
                        str(panel_info['modules'][chanel]['installed'])), 'Installed for %s is %s' % (chanel,
                                                                                                      str(status)))

    def CheckPanelOnGUI(self, serial: str, status: bool):
        time.sleep(1.5)
        if status:
            self.AssertTrue(self.GuiApi.Units.getUnitId(serial), 'Panel %s is not displayed on GUI' % serial,
                            'Panel %s displayed on GUI' % serial)
        else:
            self.AssertNotTrue(self.GuiApi.Units.getUnitId(serial), 'Panel %s displayed on GUI' % serial,
                               'Panel %s is not displayed on GUI' % serial)

    def CheckPanelInRedis(self,  panel: object, status: bool):
        if status:
            self.AssertTrue(panel.serial in self.SSH.getPanelsFromRedis(),
                            'No entries with panels(%s) ID in redis' % panel.serial,
                            'Entries with panels(%s) ID in redis' % panel.serial)
        else:
            self.AssertNotTrue(panel.serial in self.SSH.getPanelsFromRedis(),
                               'Entries with panels(%s) ID in redis' % panel.serial,
                               'No entries with panels(%s) ID in redis' % panel.serial)

    def CheckUntModel(self, panel: 'NeoPanel', unt_model: str):
        panel_info = self.GetPanelInfo('FF' + panel.serial)
        self.AssertTrue(panel_info['unt_model'] == unt_model,
                        'Panel is displayed on Panels page without "%s" model' % unt_model,
                        'Panel is displayed on Panels page with %s" model' % unt_model)

    def ChangeHeartbeatPeriodForGroup(self, access_type: str, chanel: str, supervision: int, timeout: int,
                                      name_group: str = 'Main Group'):
        """
        access_type - pmaster, quazar, quazar53
        chanel - bba, gprs
        """
        comm = {"pmaster": {"bba": {"isEnabled": True, "supervision": 5, "timeout": 130},
                            "gprs": {"isEnabled": True, "supervision": 120, "timeout": 130}},
                "quazar": {"bba": {"isEnabled": True, "supervision": 120, "timeout": 130},
                           "gprs": {"isEnabled": True, "supervision": 120, "timeout": 130}},
                "quazar53": {"bba": {"isEnabled": True, "supervision": 120, "timeout": 130},
                             "gprs": {"isEnabled": True, "supervision": 120, "timeout": 130}}}
        if access_type == 'quazar':
            for ch in ['bba', 'gprs']:
                comm[access_type][ch]['supervision'] = supervision
                comm[access_type][ch]['timeout'] = timeout
        else:
            comm[access_type][chanel]['supervision'] = supervision
            comm[access_type][chanel]['timeout'] = timeout

        self.AddMessage('Set %s(%s) in "%s" to supervision - "%s" timeout - "%s" ' % (access_type, chanel, name_group,
                                                                                      supervision, timeout))
        if timeout - supervision < 10: self.AddFailure('Must be greater than or equal to %s' % str(supervision + 10))
        res = self.GuiApi.Group.editGroup(name=name_group, communications=comm)
        self.AssertResponseCode(res, 200)

    def setSupervisionForGroup(self, access_type: str, bba: bool = True, gprs: bool = True,
                               name_group: str = 'Main Group'):
        """
        access_type - pmaster, quazar, quazar53
        """
        comm = {"pmaster": {"bba": {"isEnabled": True, "supervision": 180, "timeout": 240},
                            "gprs": {"isEnabled": True, "supervision": 180, "timeout": 240}},
                "quazar": {"bba": {"isEnabled": True, "supervision": 135, "timeout": 405},
                           "gprs": {"isEnabled": True, "supervision": 135, "timeout": 405}},
                "quazar53": {"bba": {"isEnabled": True, "supervision": 135, "timeout": 405},
                             "gprs": {"isEnabled": True, "supervision": 135, "timeout": 405}}}
        comm[access_type]['bba']['isEnabled'] = bba
        comm[access_type]['gprs']['isEnabled'] = gprs
        self.AddMessage(
            'Set %s in "%s" to bba - "%s" gprs - "%s" ' % (access_type, name_group, str(bba), str(gprs)))
        res = self.GuiApi.Group.editGroup(name=name_group, communications=comm)
        self.AssertResponseCode(res, 200)

    def setTimeSynchronizationForGroup(self, enabled: bool, upgrade_method: str, name_group: str = 'Main Group'):
        """

        :param enabled: True or False
        :param upgrade_method:  bba or gprs
        :return:
        """
        options = {True: 'Enabled', False: 'Disabled'}
        self.AddMessage('%s time synchronization and set upgrade method - %s' % (options[enabled], upgrade_method))
        res = self.GuiApi.Group.editGroup(name=name_group, timeSynchronization=enabled, upgradeMethod=upgrade_method)
        self.AssertResponseCode(res, 200)

    def GetPanelInfo(self, panel_serial):
        panel = None
        for timer in StopWatch(4, 0.1):
            panel = self.GuiApi.Units.getUnit(unt_serial=panel_serial)
            if panel: return panel
        self.AssertTrue(panel, 'Did not receive information about the panel %s' % panel_serial)

    def waitPanelDisconnected(self, serial: str, timeout=20, frequency=0.1):
        if self.GuiApi.Units.getUnitId(serial):
            for timer in StopWatch(timeout, frequency):
                panel_info = self.GetPanelInfo(serial)
                if not panel_info['modules']['bba']['connected'] and not panel_info['modules']['gprs']['connected']:
                    self.AddSuccess('Connected for bba and gprs is False')
                    return
            self.AddFailure('Panel %s connected to server after %s' % (serial, timeout))
        return
    
    def wakeUpPanelOnUserInitiatedDiscovery(self, enable=False):
        self.AddMessage(f'Set wake up on trigger discovery to {enable}')
        response = self.GuiApi.MMI.setWakeUpOnUserDiscovery(enable=enable)
        self.CheckResponseCodeStatusSuccess(response, 200, 'success')

    def waitThreadStopped(self, thread: 'Thread', timeout: int = 10, frequency: int = 0.1):
        self.AddMessage('wait thread stopped')
        for timer in StopWatch(timeout, frequency):
            thread_status = thread.is_alive()
            if not thread_status:
                self.AddSuccess('Thread is stopped ')
                thread.join()
                return
        self.AddFailure('Thread not stopped ')

    def AutoenrollmentForChanel(self, channel: str, value: bool):
        self.AssertLoginWasSuccess(usr_email=self.web.email, usr_password=self.web.password)
        channels = {'bba': 'broadband', 'gprs': 'cellular'}
        self.AddMessage("%s Automatic enrollment for %s" % ('Enabled' if value else 'Disabled',
                                                            channels[channel].title()))
        response = self.GuiApi.MMI.changeOptions(option='%s_settings' % channels[channel],
                                                 isAutoEnrollmentEnabled=value)
        self.AssertResponseStatusCode(response, 200)

    def setFibroAcceptEventBeforeDiscovery(self, status: bool):
        acc_ev_status = ['Enabled', 'Disabled']
        self.AddMessage('Set fibro accept event before discovery %s' % str(status))
        self.AssertTrue(self.SSH.setFibroAcceptEventBeforeDiscoveryCompeted(enable=status), 'SSH command failed',
                        'Accept event before discovery completed is %s' % acc_ev_status[status == False])

    def CheckPanelEventOnServer(self, serial: str):
        resp = self.GuiApi.Events.get_all_events().json()
        event_on_enent_page = False
        if len(resp['data']['rows']) != 0:
            for row in resp['data']['rows']:
                if row['unt_serial'] == serial:
                    event_on_enent_page = True
        return event_on_enent_page

    def CheckPanelEventsOnServer(self, serial: str, status: bool):
        resp = self.GuiApi.Events.get_all_events().json()
        event_on_event_page = False
        if len(resp['data']['rows']) != 0:
            for row in resp['data']['rows']:
                if row['unt_serial'] == serial:
                    event_on_event_page = True
        if status:
            self.AssertTrue(event_on_event_page,
                            'Event from panel is not displayed on Events page',
                            'Event from panel is displayed on Events page')
        else:
            self.AssertNotTrue(event_on_event_page,
                               'Event from panel is displayed on Events page',
                               'Event from panel is not displayed on Events page')

    def CheckAllDiscoveryStagesInRedis(self, serial: str):
        self.AddMessage('Check discovery stages in Redis ')
        discovery_stages = self.SSH.GetDiscoveryStages(serial)
        for name, value in discovery_stages.items():
            self.AssertTrue(value == '1', '%s is %s' % (name, value), '%s is %s' % (name, value))

    def getValuesAllDiscoveryStagesInRedis(self, serial: str) -> list:
        self.AddMessage('Get values all discovery stages in Redis')
        return [item for item in self.SSH.GetDiscoveryStages(serial).values()]

    def CheckDiscoveryStageInRedis(self, serial: str, discovery: str, value: str):
        """
        :param serial:
        :param discovery:
        :param value: 1 or 0
        :return:
        """
        self.AddMessage('Check %s stages in Redis' % discovery)
        discovery_stages = self.SSH.GetDiscoveryStages(serial)
        self.AssertTrue(discovery_stages[discovery] == value, 'Incorrect %s - %s' % (discovery,
                                                                                     discovery_stages[discovery]),
                        '%s is %s' % (discovery, value))

    def checkDiscoveryStageListInRedis(self, serial: str, discovery_stages: list, value: str):
        self.AddMessage('Check discovery stage in Redis')
        disc_stages_in_redis = self.SSH.GetDiscoveryStages(serial)
        for stage in discovery_stages:
            self.AssertTrue(disc_stages_in_redis.get(stage) == value, 'Incorrect %s - %s' % (stage,
                            disc_stages_in_redis.get(stage)), '%s is %s' % (stage, value))

    def CheckFaultForPanel(self, serial: str, trouble: str):
        self.AddMessage('Get faults for panel %s' % serial)
        faults = self.GetPanelInfo(serial)['faults']
        for fault in faults:
            if fault['iow_id'] == trouble:
                return True
        return False

    def CheckFaultSuspended(self, serial: str, fault_id: str):
        self.AddMessage('Get faults for panel %s' % serial)
        faults = self.GetPanelInfo(serial)['faults']
        for fault in faults:
            if fault['utf_id'] == fault_id:
                return fault['suspended']
        self.AssertTrue(False, 'Fault not found for panel %s' % serial)

    def CheckStateForPanel(self, serial: str, state: str, partition: int = 1):
        correct_state = False
        data = False
        unt_id = self.GuiApi.Units.getUnitId(serial)
        for timer in StopWatch(30, 0.1):
            if data:
                break
            response = self.GuiApi.Diagnostic.get_state(unt_id=unt_id).json()
            if response['data']['state']:
                data = True
                for timer in StopWatch(10, 0.1):
                    response = self.GuiApi.Diagnostic.get_state(unt_id=unt_id).json()
                    if response['data']['state'][partition - 1]['state'] == state:
                        correct_state = True
                        self.AddSuccess('State for panel(partition %d) is %s' % (partition, state))
                        break
        self.ExpectTrue(correct_state, 'State for panel(partition %d) is not %s, state is %s' %
                        (partition, state, response['data']['state']))

    def addAllDeviceToNeo(self, panel: 'NeoPanel'):
        for name in DeviceNames.keys():
            if name.upper() == 'SYSTEM': continue
            if name.upper() == 'WIRED_ZONE' and len(panel.config.devices.detector) > 16 \
                    and panel.config.model == 'HS2016_4':
                panel.add_device(name, 1)
                continue
            panel.add_device(name, 0)

    def _addHwIOVAndWiredZoneToPmax(self, panel: 'PmaxPanel'):
        for i in range(1, panel.config.devices.hw_iov._size + 1):
            panel.add_device('HW_IOV', 0)
            for number in range(1, 5):
                panel.addHWDevice(dev_name='WIRED_ZONE_HW_IOV', parent=i, port=0)

    def addAllDeviceToPmax(self, panel: 'PmaxPanel'):
        self.AddMessage('Add all device to Pmax panel')
        if 'hw_iov' not in panel.config.devices.keys():
            panel.config.devices._support_expander()
            self._addHwIOVAndWiredZoneToPmax(panel)
        for name in devdbDeviceNames.keys():
            if name in ('HW_IOV', 'WL_IOV', 'WIRED_ZONE_HW_IOV', 'WIRED_ZONE_WL_IOV', 'WIRED_ZONE_EXP', 'PGM_HW_IOV',
                        'PGM_EXP', 'PGM_HW_IOV', 'PGM_EXPANDER', 'PGM_WL_IOV'):
                continue
            panel.add_device(name, 0)

    def AddMaxDeviceForPanel(self, panel: object):
        """
        :param panel: NeoPanel or PmaxPanel
        """
        self.AddMessage('Add maximum devices to panel')
        add_device = True
        while add_device:
            for table in panel.config.devices.classes:
                if len(table) != table._size and table.code != 0:
                    if type(panel) is NeoPanel:
                        self.addAllDeviceToNeo(panel)
                        break
                    elif type(panel) is PmaxPanel:
                        self.addAllDeviceToPmax(panel)
                        break
            else:
                add_device = False

    def waitDiscoveryStagesCheckInRedis(self, serial: str, discovery_stages: list):
        for name in discovery_stages:
            stages = self.SSH.getNeoDiscoveryStages(serial)
            if name not in stages: self.waitDiscoveryStageAppearedInRedis(serial, name, timeout=30.00)
            # if name == discovery_stages[0]: self.waitDiscoveryStageAppearedInRedis(serial, name)
            if self.waitDiscoveryStage(serial, name):
                continue
            else:
                self.ExpectWasSuccesfull(False, 'Discovery was not finished')

    def chekUserFieldsInPmaxUserTableIsNotNull(self, panel: object):
        result = self.GetAllUserFromPmaxUsers(panel.config.serial)
        for users in result:
            self.ExpectTrue(users['pxu_code'], 'User code  for %s not saved' % users['pxu_label'],
                            'User code(%s) saved for %s' % (users['pxu_code'], users['pxu_label']))
            self.ExpectTrue(users['pxu_partitions'], 'Partitions for %s not saved' % users['pxu_label'],
                            'Partitions saved for %s' % users['pxu_label'])
            if type(panel) is NeoPanel:
                self.ExpectTrue(users['pxu_label'], 'Label for user_id %s not saved' % users['pxu_panel_id'],
                                'Label saved for user_id %s' % users['pxu_panel_id'])
            self.ExpectTrue(users['pxu_permissions'], 'Permissions  for %s not saved' % users['pxu_label'],
                            'Permissions saved for %s' % users['pxu_label'])

    def refreshRSSI(self, serial: str):
        unt_id = self.GuiApi.Units.getUnitId(serial)
        self.AddMessage('Refresh RSSI for panel {} unt_id:{}'.format(serial, unt_id))
        resp = self.GuiApi.Diagnostic.start_rssi(unt_id=unt_id)
        prs_id = resp.json()['data']['prs_id']
        self.AssertResponseStatusCode(resp, 200)
        self.AssertTrue(self.GuiApi.Processes.waitForStatus(prs_id, 'start'), 'Process Refresh RSSI not start',
                        'Process Refresh RSSI is start')
        return prs_id

    def refreshConfiguration(self, serial: str):
        unt_id = self.GuiApi.Units.getUnitId(serial)
        self.AddMessage('Start download configuration')
        resp = self.GuiApi.Configuration.refresh(unt_id=unt_id)
        self.AssertResponseStatusCode(resp, 200)
        prs_id = self.getPrsId(resp)
        return prs_id

    def checkProcessStatus(self, serial: str, process: str, status: str, unit_id=None):
        all_process = self.getAllProccesForPanel(serial, unit_id)
        found_process = False
        for item in all_process:
            if item['prs_type'] == process:
                found_process = True
                self.AssertTrue(item['prs_status'] == status, 'Process (%s) status not is %s' % (process, status),
                                'Process(%s) status is %s' % (process, status))
        self.AssertTrue(found_process, 'Process %s - Not found' % process)

    def checkProcessStatusById(self, prs_id: int, status: str,):
        prs = self.GuiApi.Processes.getProcessById(prs_id)
        self.AssertTrue(prs['prs_status'] == status, 'Process ({}) status is {} instead expected {}'.format(prs_id, prs['prs_status'], status),
                        'Process({}) status is {}'.format(prs_id, status))
        if prs is False:
            self.AddFailure('Process {} - Not found'.format(prs_id))

    def checkProcessErrorMessage(self, serial: str, process: str, error_message: str, unit_id=None):
        all_process = self.getAllProccesForPanel(serial, unit_id)
        found_process = False
        for item in all_process:
            if item['prs_type'] == process:
                found_process = True
                self.AssertTrue(item['prs_error_message'] == error_message,
                                'Process (%s) erro message not is %s' % (process, error_message),
                                'Process(%s) error message is %s' % (process, error_message))
        self.AssertTrue(found_process, 'Process %s - Not found' % process)

    def getIdEventsForPanel(self, serial: str) -> list:
        id_events = []
        unt_id = self.GuiApi.Units.getUnitId(serial)
        self.AddMessage('Get all events for panel -%s' % serial)
        resp = self.GuiApi.Events.get_all_events(filter='unt_id=%s' % unt_id)
        for event in resp.json()['data']['rows']:
            id_events.append(event['evt_id'])
        return id_events

    def checkEventForPanel(self, serial: str, event: str, existing_evt_id: list, timeout: int = 10,
                           frequency: float = 0.1):
        unt_id = self.GuiApi.Units.getUnitId(serial)
        self.AddMessage('Get all events for panel - %s' % serial)
        event_found = False
        event_id = None
        for timer in StopWatch(timeout, frequency):
            resp = self.GuiApi.Events.get_all_events(filter='unt_id=%s' % unt_id)
            for item in resp.json()['data']['rows']:
                if item['evt_description'].lower() == event.lower() and item['evt_id'] not in existing_evt_id:
                    event_found = True
                    event_id = item['evt_id']
                    break
            if event_found: break
        self.ExpectTrue(event_found, 'Event %s NOT present on GUI for panel %s after %s' % (event, serial, timeout),
                        'Event %s present on GUI for panel %s ' % (event, serial))
        return event_id

    def checkEventNameWithVideoForPanel(self, serial: str, event_name: str, timeout: int = 15, frequency: float = 0.1):
        unt_id = self.GuiApi.Units.getUnitId(serial)
        self.AddMessage('Get all events for panel - %s' % serial)
        event_found = False
        video = False
        evt_id = None
        for timer in StopWatch(timeout, frequency):
            resp = self.GuiApi.Events.get_all_events(filter='unt_id=%s' % unt_id)
            for item in resp.json()['data']['rows']:
                if item['evt_description'].lower() == event_name.lower():
                    if item['evt_path'] and '/ha_shared/ipmp/eventsPictures' in item['evt_path']:
                        video = True
                        evt_id = int(item['evt_id'])
                    event_found = True
                    break
        self.ExpectTrue(event_found, 'Event %s NOT present on GUI for panel %s after %s' % (event_name, serial, timeout),
                        'Event %s present on GUI for panel %s ' % (event_name, serial))
        self.ExpectTrue(video, 'Film not present in /ha_shared/ipmp/eventsPictures',
                        'Film present in /ha_shared/ipmp/eventsPictures')
        if event_found : return evt_id

    def createNewGroup(self, name: str = 'Secondary Group') -> int:
        self.AddMessage('Create group with name - %s' % name)
        response = self.GuiApi.Group.create(
                  **{"name": name, "description": "test", "localWakeUp": True,
                  "upgradeMethod": "gprs", "BBAEncryption": True,
                  "timeSynchronization": True, 'pscConnection': False,
                  "serverMessagingLanguage": None, "serverMessagingLanguageId": 1,
                  "communications":
                      {"pmaster": {"bba": {"isEnabled": True, "supervision": 10, "timeout": 20},
                                   "gprs": {"isEnabled": True, "supervision": 120, "timeout": 130}},
                       "quazar": {"bba": {"isEnabled": True, "supervision": 120, "timeout": 130},
                                  "gprs": {"isEnabled": True, "supervision": 120, "timeout": 130}},
                       "quazar53": {"bba": {"isEnabled": True, "supervision": 120, "timeout": 130},
                                    "gprs": {"isEnabled": True, "supervision": 120, "timeout": 130}}}})
        self.ExpectResponseCode(response, 200)
        return response.json()['data']['utg_id']

    def checkDiscoveryIsStarted(self, serial: str, timeout: int = 5):
        start = False
        for _ in StopWatch(timeout, 1):
            if '0' in [item for item in self.SSH.GetDiscoveryStages(serial).values()]:
                start = True
                break
        self.ExpectTrue(start, 'Discovery not started', 'Discovery started')

    def checkDiscoveryIsNotStarted(self, serial: str):
        start = False
        for _ in StopWatch(5, 1):
            if '0' in [item for item in self.SSH.GetDiscoveryStages(serial).values()]:
                start = True
                break
        self.ExpectTrue(not start, 'Discovery started', 'Discovery not started')

    def waitFaultRemoved(self, serial: str, fault: str):
        for timer in StopWatch(15, 1):
            faults = self.GetPanelInfo(serial)['faults']
            faults_list = [i['iow_id'] for i in faults] if faults else faults
            if fault not in faults_list:
                self.AddSuccess('%s not displayed' % fault)
                return
        self.AddFailure('Fault %s present on GUI for %d seconds' % (fault, 15))

    def checkDiscoveryIsFinished(self, serial: str):
        self.ExpectTrue('0' not in [i for i in self.getValuesAllDiscoveryStagesInRedis(serial)],
                        'Discovery is not finished', 'Discovery is finished, all stages in redis are 1')
        self.waitFaultRemoved(serial, 'DISCOVERY_NOT_FINISHED_TROUBLE')

    def waitWarningRemoved(self, serial: str, warning: str, timeout: int = 15, frequency: int = 1):
        for timer in StopWatch(timeout, frequency):
            data = self.getWarning(serial)
            self.AddMessage(data)
            warning_list = [i['iow_id'] for i in data] if data else []
            if warning not in warning_list:
                self.AddSuccess('%s deleted in warning table' % warning)
                return
        self.AddFailure('Warning %s present in warning table after %s sec' % (warning, timeout))

    def initiateWebSocket(self):
        self.AddMessage('Init web socket')
        return WebSocket()

    def refreshState(self, serial: str) -> int:
        self.AddMessage('Start process - Refresh state ')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.refreshPanel(unt_id)
        self.AssertTrue(response.status_code == 200, 'Process is not started', 'Process is started')
        return response.json()['data']['prs_id']

    def refreshGsm(self, serial: str) -> int:
        self.AddMessage('Start process - Refresh gsm ')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.refreshGsm(unt_id)
        self.AssertTrue(response.status_code == 200, 'Process is not started', 'Process is started')
        return response.json()['data']['prs_id']

    def refresh_state_for_several_panel(self, serials: list) -> dict:
        self.AddMessage('Refresh state for panels %s' % str(serials))
        unt_id = [self.GuiApi.Units.getUnitId(serial) for serial in serials]
        resp = self.GuiApi.UnitsFaulty.refresh(unt_id=unt_id, batch_id=self.randomStringDigits())
        self.AssertResponseStatusCode(resp, 200)
        return self.getPrsIds(resp)

    def downloadConfiguration(self, serial: str) -> int:
        self.AddSuccess('Start Download configuration')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Configuration.refreshConfiguration(unt_id)
        self.AssertTrue(response.status_code == 200, 'Process is not started', 'Process is started')
        return self.getRunnerPrsId(response)

    def startWalkTest(self, serial: str) -> int:
        self.AddSuccess('Start Walk test')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.startWalkTest(unt_id)
        self.AssertTrue(response.status_code == 200, 'Process is not started', 'Process is started')
        return response.json()['data']['prs_id']

    def stopWalkTest(self, serial: str):
        self.AddSuccess('Stop Walk test')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        resrponse = self.GuiApi.Diagnostic.walktest_stop(unt_id=unt_id)
        self.CheckResponseCodeStatusSuccess(resrponse)

    def videoOnDemand(self, serial, utz_id):
        self.AddSuccess('Start video on demand')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.requestVideo(unt_id, utz_id)
        self.CheckResponseCodeStatusSuccess(response)
        return response.json()['data']['prs_id']

    def startRssi(self, serial: str) -> int:
        self.AddSuccess('Start Refresh RSSI')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.startRSSI(unt_id)
        self.CheckResponseCodeStatusSuccess(response)
        return response.json()['data']['prs_id']

    def startRRI(self, serial: str) -> int:
        self.AddSuccess('Start RRI')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.RemoteInspection.initiateInspection(unt_id=[unt_id])
        self.CheckResponseCodeStatusSuccess(response)
        return response.json()['data']['processes'][0]['prs_id']

    def getDetectorId(self,panel: PmaxPanel, name: str) -> int:
        for item in panel.config.devices.detector:
            if item.name == name:
                return item.number

    def checkSession(self, thread: 'Thread', status: bool):
        if not status:
            self.AssertNotTrue(thread.is_alive(), 'Sessions is not closed', 'Session closed')
            thread.join()
        else:
            self.AssertTrue(thread.is_alive(), 'Session closed', 'Sessions is not closed')

    def wait(self, timeout: int):
        self.AddSuccess('Wait %s sec' % timeout)
        time.sleep(timeout)
        self.AddSuccess('Wait is over')

    def waitProcessStatus(self, prs_id: int, status: str, timeout=90):
        self.AddMessage('Wait process is %s' % status)
        self.ExpectTrue(self.GuiApi.Processes.waitForStatus(prs_id, status, timeout),
                        'Process is not %s' % status.title(), 'Process is %s' % status.title())

    def check_process_stages(self, prs_id: int, stages: tuple):
        self.AddMessage('Wait process stages - %s' % str(stages))
        for stage in stages:
            self.AddMessage('Wait stage - %s' % stage)
            details = ''
            test = False
            for _ in StopWatch(10, 1):
                if not test:
                    processes = self.GuiApi.Processes.getProcesses()
                    for prs in processes:
                        if prs['prs_id'] == str(prs_id):
                            details = prs['prs_details']
                            if prs['prs_details'] == stage:
                                test = True
                                self.AddSuccess('Correct process stage - %s' % stage)
                                break
                else:
                    break
            self.ExpectTrue(test, 'Incorrect stage - %s after 10 sec' % details)

    def check_process_stages_and_percentage(self, prs_id: int, stages: dict):
        self.AddMessage('Wait process stages - %s' % str(stages))
        for stage, percentage in stages.items():
            self.AddMessage('Wait stage - %s' % stage)
            details = ''
            test = False
            for _ in StopWatch(60, 1):
                if test:
                    break
                prs = self.GuiApi.Processes.getProcessById(prs_id)
                details = prs['prs_details']
                if prs['prs_details'] == stage:
                    test = True
                    self.AddSuccess('Correct process stage - %s' % stage)
                    for per in percentage:
                        percent = False
                        for _ in StopWatch(60, 1):
                            if percent:
                                break
                            pro = self.GuiApi.Processes.getProcessById(prs_id)
                            prs_percentage = pro['prs_percentage']
                            if pro['prs_percentage'] == str(per):
                                percent = True
                                self.AddSuccess('Correct process stage percentage %d' % per)
                                break
                        self.ExpectTrue(percent, 'Incorrect percent - %s' % prs_percentage)
            self.ExpectTrue(test, 'Incorrect stage - %s after 60 sec' % details)

    def enableBypassZone(self, serial: str, zone_number: int) -> int:
        self.AddMessage('Enable bypass zone - %d' % zone_number)
        unt_id = self.GuiApi.Units.getUnitId(serial)
        device_id = self.GuiApi.Diagnostic.getDeviceId(unt_id, 'ZONE', zone_number)
        response = self.GuiApi.Diagnostic.bypass(enabled=True, utz_id=[device_id])
        self.CheckResponseCodeStatusSuccess(response)
        return response.json()['data']['processes'][0]['prs_id']

    def setState(self, serial: str, partition: int, state: str) -> int:
        self.AddMessage('Set state -  %s(panel %s, partition %d)' % (state, serial, partition))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.set_state(unt_id=unt_id, partition=partition, state=state)
        self.CheckResponseCodeStatusSuccess(response)
        return response.json()['data']['prs_id']

    def downloadLog(self, serial: str) -> int:
        self.AddMessage('Download log for panel %s' % serial)
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Log.refresh_log(unt_id=unt_id)
        self.CheckResponseCodeStatusSuccess(response)
        return response.json()['data']['prs_id']

    def stopProcess(self, prs_id: int):
        self.AddMessage('Stop process %s' % prs_id)
        response = self.GuiApi.Processes.stop_process(prs_id=[prs_id])
        self.CheckResponseCodeStatusSuccess(response)

    def enableUserApp(self, serial: str):
        self.AddMessage('Enable User App for panel')
        response = self.GuiApi.Units.user_app_enable(unitId=self.GuiApi.Units.getUnitId(serial), state=True)
        self.CheckResponseCodeStatusSuccess(response)

    def checkStatusStateOpen(self, serial: str, label: str, status: str):
        """
        :param status: yes or no
        :return:
        """
        self.ExpectTrue(self.getUnitValueFromUnitZone(serial, label)['utz_state_open'] == status,
                        'utz_state_open for %s is not %s' % (label, status),
                        'utz_state_open for %s is %s' % (label, status))

    def getTemperatureData(self, serial: str, device_number: int, device_type: str = 'ZONE'):
        self.AddMessage('Get Temperature data for %s %s' % (device_type, device_number))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        utz_id = self.GuiApi.Diagnostic.getDeviceId(unt_id, device_type, device_number)
        responce = self.GuiApi.Diagnostic.get_temperature(unt_id=unt_id, utz_id=utz_id)
        self.CheckResponseCodeStatusSuccess(responce)
        return responce.json()['data']

    def randomStringDigits(self, stringLength: int = 10) -> str:
        """Generate a random string of letters and digits """
        lettersAndDigits = string.ascii_lowercase + string.digits
        data = ''.join(random.choice(lettersAndDigits) for _ in range(stringLength - 1))
        return '1' + data

    def triggerDiscovery(self, serial: str, timeout: int = 600):
        self.AddMessage('Stater trigger discovery for %s panel timeout - %s' % (serial, str(timeout)))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Units.forceDiscovery(serial, timeout=timeout)
        self.AssertResponseStatusCode(response, 200)
        return self.getPrsId(response)

    def get_id_basic_conf(self, name: str):
        self.AddMessage('Get all config')
        response = self.GuiApi.BasicConfiguration.list()
        self.AssertResponseStatusCode(response, 200)
        found = False
        for conf in response.json()['data']['rows']:
            if conf['pca_name'] == name:
                found = True
                return int(conf['pca_id'])
        self.AssertTrue(found, 'Basic conf with name %s was not found' % name)

    def make_basic_config(self, serial: str, diff: list, name: str) -> int:
        self.AddMessage('Make basic configuration with diff - %s' % str(diff))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Configuration.add_basic(unt_id=unt_id, diff=diff, name=name)
        self.AssertResponseStatusCode(response, 200)
        return self.get_id_basic_conf(name)

    def upload_basic_config(self, serials: list, pca_id: int):
        self.AddMessage('Upload basic configuration for %s panel' % str(serials))
        unt_id = []
        for serial in serials:
            unt_id.append(self.GuiApi.Units.getUnitId(serial))
        resp = self.GuiApi.BasicConfiguration.uploadBasicConfig(unt_id, pca_id)
        self.AssertResponseStatusCode(resp, 200)
        return self.getPrsIds(resp)

    def remove_basic_config(self, pca_id: int):
        self.AddMessage('Remove basic config with id %d' % pca_id)
        resp = self.GuiApi.BasicConfiguration.remove(pca_id=[pca_id])
        self.AssertResponseStatusCode(resp, 200)

    def upload_config(self, serial: str, diff: list, version: int):
        self.AddMessage('Upload config for %s panel with diff - %s' % (serial, str(diff)))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        resp = self.GuiApi.Configuration.uploadConfig(unt_id, version, diff)
        return self.getRunnerPrsId(resp)

    def refresh_all_config(self, serials: list):
        self.AddMessage('Refresh config for panels %s' % str(serials))
        unt_ids = []
        for serial in serials:
            unt_ids.append(self.GuiApi.Units.getUnitId(serial))
        resp = self.GuiApi.Configuration.massRefreshConfig(unt_ids)
        self.AssertResponseStatusCode(resp, 200)
        return self.getPrsIds(resp)

    def wait_trouble(self, serial: str, trouble: str, timeout: int = 10):
        present = False
        for _ in StopWatch(timeout, 1):
            result = self.CheckTroubleForPanelInDB(serial, trouble)
            if result:
                present = True
                self.AddSuccess('%s for %s Panel is present in the warning table' % (trouble, serial))
                break
        self.ExpectTrue(present, '%s for %s Panel is present in the warning table' % (trouble, serial))

    def enable_system_offline_events(self, one_channel: bool, two_channel: bool):
        self.AddMessage('Set system ofline event for one_chanel=%s, two_channel=%s' % (str(one_channel), str(two_channel)))
        status = [None, 'on']
        resp = self.GuiApi.MMI.changeOptions(option='supervision', doSendOneChannelPanelOnlineOffline=one_channel,
                                             doSendTwoChannelPanelOnlineOffline=two_channel)
        self.AssertResponseStatusCode(resp, 200)

    def set_supervision_settings(self, email: bool, sms: bool, one_chanel: bool, two_chanel: bool):
        self.AddMessage('Set sendEmail - %s, sendSms - %s, oneChanel - %s, twoChanel - %s' % (sms, email, one_chanel,
                                                                                              two_chanel))
        response = self.GuiApi.MMI.setSupervision(email, sms, one_chanel, two_chanel)
        self.AssertResponseCode(response, 200)
    def set_auto_enrollment_mask(self, mask: str):
        self.AddMessage('Set Autoenroll mask %s' % mask)
        resp = self.GuiApi.MMI.changeOptions(option='common', systemIdRegex=mask)
        self.AssertResponseStatusCode(resp, 200)

    def set_remove_panel_forever(self, value: bool):
        self.AddMessage('set remove panel forever - %s' % str(value))
        resp = self.GuiApi.MMI.changeOptions(option='common', isPanelRemoveForever=value)
        self.AssertResponseStatusCode(resp, 200)

    def get_firmware(self, serial: str, type_appliance: str) -> list:
        self.AddMessage('Get firmware packages for Panels %s - %s' % (serial, type_appliance))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        resonse = self.GuiApi.Firmware.list(unt_id=unt_id)
        self.AssertResponseStatusCode(resonse, 200)
        for appliance in resonse.json()['data']['appliances']:
            if appliance['type'] == type_appliance:
                return appliance['packages']
        self.AddWarning('Packages not found')
        return list()

    def get_listappliance(self, type_appliance: str) -> list:
        self.AddMessage('Get listappliance on general Firmware Tab for %s' % type_appliance)
        resonse = self.GuiApi.Firmware.listappliance()
        self.AssertResponseStatusCode(resonse, 200)
        for appliance in resonse.json()['data']:
            if appliance['utd_rest_name'] == type_appliance:
                return appliance['upgrade_packages']
        self.AddWarning('Packages not found')
        return list()

    def start_upgrade(self, serial: str, device_type: str, package: str, timeout: int = 86400, fail_on_armed: bool = True):
        self.AddMessage('Start upgrade for %s device type %s failed on panel armed - %s' %
                        (serial, device_type, str(fail_on_armed)))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Firmware.upgradeUnit(unt_id=unt_id,
                                                    packages=[{"device_type": "%s" % device_type,
                                                               "package": "%s" % package}],
                                                    timeout=timeout,
                                                    fail_on_armed_state=fail_on_armed)
        self.AssertResponseStatusCode(response, 200)
        batch_id = response.json()['data']['batch_id']
        return batch_id

    def start_muss_upgrade(self,
                           serials: list,
                           device_type: str,
                           package: str,
                           timeout: int = 86400,
                           fail_on_armed: bool = True):
        self.AddMessage('Start upgrade for %s device type %s failed on panel armed - %s' %
                        (str(serials), device_type, str(fail_on_armed)))
        response = self.GuiApi.Firmware.listappliance()
        self.AssertResponseStatusCode(response, 200)
        uep_id = ''
        for appliance in response.json()['data']:
            if appliance['utd_rest_name'] == device_type:
                for pack in appliance['upgrade_packages']:
                    if pack['uep_name'] == package:
                        uep_id = int(pack['uep_id'])
        self.AssertTrue(uep_id, 'Package id not found')
        unt_id = []
        for serial in serials:
            unt_id.append(self.GuiApi.Units.getUnitId(serial))
        response = self.GuiApi.Firmware.massUpgrade(unt_id=unt_id, timeout=timeout, uep_id=uep_id,
                                                    fail_on_armed_state=fail_on_armed)
        self.AssertResponseStatusCode(response, 200)
        batch_id = response.json()['data']['id']
        return batch_id

    def get_process_id_from_runner(self, batch_id, serial, time_out=30):
        for _ in StopWatch(time_out, frequency=0.5):
            response = self.GuiApi.Firmware.upgrade_status_runners(batch_id=batch_id)
            self.CheckResponseCodeStatusSuccess(response)
            for row in response.json()['data']['rows']:
                if row['_unt_serial'] == serial:
                    if row['prs_id']: return int(row['prs_id'])
        return

    def get_runner_id_from_runner(self, batch_id, serial, time_out=30):
        for _ in StopWatch(time_out, frequency=0.5):
            response = self.GuiApi.Firmware.upgrade_status_runners(batch_id=batch_id)
            self.CheckResponseCodeStatusSuccess(response)
            for row in response.json()['data']['rows']:
                if row['_unt_serial'] == serial:
                    if row['runner_id']: return int(row['runner_id'])
        return

    def retry_runner(self, runner_id: list) -> str:
        self.AddMessage('Retry runner id %s' % str(runner_id))
        batch_id = self.randomStringDigits()
        response = self.GuiApi.Firmware.runners_retry(batch_id=batch_id, runner_ids=runner_id)
        self.AssertResponseStatusCode(response, 200)
        return batch_id

    def check_packages_for_appliance_panel_tab(self, serial: str, type_appliance: str, packages: list):
        self.AddMessage('Check packages for Panel %s - %s' % (serial, type_appliance))
        if packages:
            result = [i['name'] for i in self.get_firmware(serial, type_appliance)]
            self.ExpectTrue(len(result) == len(packages), 'Incorrect quantity packages', 'Correct quantity packages')
            for package in packages:
                self.ExpectTrue(package in result,'Upgrade package %s is NOT displayed for %s' % (package, type_appliance),
                                'Upgrade package %s is displayed for %s' % (package, type_appliance))
        else:
            self.AddFailure('Packages not found')

    def check_packages_for_appliance_general_tab(self, type_appliance: str, packages: list):
        self.AddMessage('Check packages on general Firmware Tab for %s'% type_appliance)
        if packages:
            result = [i['uep_name'] for i in self.get_listappliance(type_appliance)]
            self.ExpectTrue(len(result) == len(packages), 'Incorrect quantity packages', 'Correct quantity packages')
            for package in packages:
                self.ExpectTrue(package in result,'Upgrade package %s is NOT displayed for %s' % (package, type_appliance),
                                'Upgrade package %s is displayed for %s' % (package, type_appliance))
        else:
            self.AddFailure('Packages not found')

    def remove_group(self, group_name: str):
        grp_id = self.GuiApi.Group.getGroupId(group_name=group_name)
        if grp_id:
            self.AddMessage('Remove group -%s' % group_name)
            res = self.GuiApi.Group.removeGroup(grp_id)
            self.ExpectResponseCode(res, 200)

    def create_user(self, role: str, name: str, email: str, pwd: str, phone: str = '+380937778899', coy_id: int = 180):
        roe_id = self.GuiApi.Roles.getRoleId(role)
        self.AssertTrue(roe_id, 'Role %s not found' % role)
        self.AddMessage('Create user email %s, pwd %s, role %s' % (email, pwd, role))
        response = self.GuiApi.User.add_user(form={'usr_name': name, 'usr_email': email, 'usr_phone': phone,
                                                   'coy_id': coy_id, 'roe_id': roe_id, 'usr_password': pwd})
        self.AssertResponseStatusCode(response, 200)
        return int(response.json()['data']['usr_id'])

    def set_firmware_permission(self, roe_id: int, firmware: bool):
        self.AddMessage('Set firmware permission - %s' % str(firmware))
        permissions = {
            'firmware': firmware,
            'firmware.unit': firmware,
            'firmware.unit.list': firmware,
            'unit.firmware.list': firmware,
            'unit.firmware.status': firmware,
            'unit.firmware.upgrade': firmware,
        }
        response = self.GuiApi.Roles.editPermissions(roe_id=roe_id, permissions=permissions)
        self.AssertResponseStatusCode(response, 200)

    def add_group_to_role(self, role_name: str, group_name: str):
        utg_id = str(self.GuiApi.Group.getGroupId(group_name))
        roles = self.GuiApi.Roles.list().json()['data']['rows']
        groups = []
        roe_id = None
        for role in roles:
            if role['roe_name'] == role_name:
                roe_id = int(role['roe_id'])
                groups = [group['utg_id'] for group in role['groups']]
                break
        self.AssertTrue(roe_id, 'Role %s not found' % role_name)
        self.AssertTrue(groups, 'Groups for %s not found' % role_name)
        groups.append(utg_id)
        response = self.GuiApi.Roles.edit_role(roe_id=roe_id, roe_name=role_name, utg_id=groups)
        self.AssertResponseStatusCode(response, 200)

    def remove_user(self, usr_id: int):
        self.AddMessage('Remove user id - %d' % usr_id)
        response = self.GuiApi.User.remove_user(usr_id=[usr_id])
        self.AssertResponseStatusCode(response, 200)

    def check_process_message(self, prs_id, message: str, timeout: int = 30):
        current_message = ''
        self.AddMessage('Wait error message - %s' % message)
        for timer in StopWatch(timeout, 0.1):
            processes = self.GuiApi.Processes.getProcesses()
            for prs in processes:
                if prs['prs_id'] == str(prs_id):
                    current_message = prs['prs_error_message']
                    if prs['prs_error_message'] == message:
                        self.AddSuccess('Correct error message - %s after %s sec' % (message, (str(timer.Value()))[:5]))
                        return
        self.AddFailure('Incorrect error message %s after %d sec' % (current_message, timeout))

    def check_process_details(self, prs_id, message: str, timeout: int = 30):
        current_message = ''
        for timer in StopWatch(timeout, 0.1):
            processes = self.GuiApi.Processes.getProcesses()
            for prs in processes:
                if prs['prs_id'] == str(prs_id):
                    current_message = prs['prs_details']
                    if prs['prs_details'] == message:
                        self.AddSuccess('Correct detail message - %s after %s sec' % (message, (str(timer.Value()))[:5]))
                        return
        self.AddFailure('Incorrect detail message %s after %d sec' % (current_message, timeout))

    def check_action_log_info(self, batch_id: str, serial: str, package: str, status: str = 'success',
                              usr_name: str = 'Default Super Admin', process: str = 'upgrade', runner_id: int = 0):
        self.AddMessage('Get action log list')
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.UserActionLog.list(count=200)
        self.AssertResponseStatusCode(response, 200)
        result = None
        for row in response.json()['data']['rows']:
            if process in row['anl_activity']:
                if row['anl_params']['batch_id'] == batch_id:
                    result = row
                    break
        self.AssertTrue(result, 'batch_id %s not found' % batch_id)
        self.ExpectTrue(result['usr_name'] == usr_name, 'Displaying incorrect name %s' % result['usr_name'],
                        'Displaying correct name')
        self.ExpectTrue(result['anl_status'] == status, 'Displaying incorrect status %s' % result['anl_status'],
                        'Displaying correct status')
        if process == 'upgrade':
            self.ExpectTrue(result['anl_data']['resolve']['unt_id'][str(unt_id)] == serial, 'Displaying incorrect serial',
                            'Displaying correct serial')
            self.ExpectTrue(result['anl_params']['packages'][0]['package'] == package, 'Displaying incorrect package',
                            'Displaying correct package')
        else:
            self.ExpectTrue(result['anl_data']['resolve']['runner_ids'][str(runner_id)]['serial'] == serial,
                            'Displaying incorrect serial',
                            'Displaying correct serial')
        try:
            self.ExpectTrue(datetime.strptime(result['anl_time'], '%Y-%m-%d %H:%M:%S')
                            and result['anl_time'] != '0000-00-00 00:00:00',
                            'Displaying incorrect time %s' % str(result['anl_time']),
                            'Displaying correct time')
        except ValueError:
            self.AddFailure('Displaying incorrect time %s' % str(result['anl_time']))

    def set_upgrade_method_for_group(self, group_name: str, method: str, gprs_for_dsc=False):
        self.AddMessage('Set upgrade method %s for group %s' % (method, group_name))
        response = self.GuiApi.Group.editGroup(group_name, upgradeMethod=method, allowUpgradeOverGprsDSCPanels=gprs_for_dsc)
        self.AssertResponseStatusCode(response, 200)

    def create_role(self, name: str, parent_role: str, group: list = [1]) -> int:
        roe_roe_id = self.GuiApi.Roles.getRoleId(parent_role)
        self.AssertTrue(roe_roe_id, 'Parent role %s not found' % parent_role)
        self.AddMessage('Create role %s parent %s' % (name, parent_role))
        response = self.GuiApi.Roles.add_role(roe_name=name, roe_roe_id=roe_roe_id, utg_id=[1])
        self.AssertResponseStatusCode(response, 200)
        return int(response.json()['data']['roe_id'])

    def remove_role(self, roe_id: list):
        self.AddMessage('Remove role id - %s' % str(roe_id))
        response = self.GuiApi.Roles.remove(roe_id=roe_id)
        self.AssertResponseStatusCode(response, 200)

    def get_quantity_panel_in_group(self, group_name) -> int:
        self.AddMessage('Get all group')
        resp = self.GuiApi.Group.get_all_groups()
        self.AssertResponseStatusCode(resp, 200)
        for group in resp.json()['data']['rows']:
            if group['name'] == group_name:
                return group['total']
        self.AssertTrue(False, 'Group %s not found' % group_name)

    def get_all_groups(self) -> list:
        self.AddMessage('Get all group')
        resp = self.GuiApi.Group.get_all_groups()
        self.AssertResponseStatusCode(resp, 200)
        return resp.json()['data']['rows']

    def create_central_station(self) -> int:
        self.AddMessage('Create CS')
        resp = self.GuiApi.CentralStations.add_cs()
        self.AssertResponseStatusCode(resp, 200)
        return int(resp.json()['data']['cls_id'])

    def remove_central_station(self, cls_id: int):
        self.AddMessage('Remove central station %s' % str(cls_id))
        resp = self.GuiApi.CentralStations.remove(cls_id=[cls_id])
        self.AssertResponseStatusCode(resp, 200)

    def wait_last_action_log(self, anl_activity: str) :
        self.AddMessage('Get action log list')
        for _ in StopWatch(10, 1) :
            response = self.GuiApi.UserActionLog.list(count=15).json()['data']['rows']
            result = sorted(response, key=lambda k : int(k['id']))
            if result[-1]['anl_activity'] == anl_activity :
                return result[-1]
        self.AssertTrue(False, '%s is not the last log' % anl_activity)

    def waitForSms(self, server, start_count, timeout=15):
        for _ in StopWatch(timeout=timeout, frequency=1):
            now_count = len(server.get_requests())
            if now_count > start_count:
                self.AddSuccess('Sms receiver Request received before: {} and now: {}'.format(start_count, now_count))
                return now_count
        else:
            self.AddFailure('Sms not received. before: {} and now: {}'.format(start_count, now_count))
            return now_count


    def edit_customer_info(self, serial: str, **param):
        self.AddMessage('Edit customer info for %s, parametуrs - %s' % (serial, param))
        settings = {
            'name': '',
            'email': '',
            'phone': '',
            'address': '',
            'remark': ''
        }
        for key, value in param.items(): settings[key] = value
        response = self.GuiApi.Units.editPanelInfo(serial, settings['name'], settings['email'], settings['phone'],
                                                   settings['address'], settings['remark'])
        self.AssertResponseCode(response, 200)

    def edit_panel_info(self, serial: str, account: str, **param):
        self.AddMessage('Edit panel info for %s, parametrs - %s' % (serial, param))
        settings = {
            'unt_serial': serial,
            'unt_account': account,
            'utg_id': 1,
            '_unt_module_gprs': 'offline',
            '_unt_module_bb': 'offline',
            'unt_sim_number': None
        }
        for key, value in param.items(): settings[key] = value
        response = self.GuiApi.Units.editPanel(serial, settings['unt_account'], settings['utg_id'],
                                               settings['_unt_module_gprs'], settings['_unt_module_bb'],
                                               settings['unt_sim_number'])
        self.AssertResponseCode(response, 200)

    def enable_temperature_and_light(self, enable: bool):
        self.AddMessage('%s temperature and light statistic' % ('Enable' if enable else 'Disable'))
        resp = self.GuiApi.Group.editGroup('Main Group', enableTemperatureAndLight=enable)
        self.AssertResponseStatusCode(resp, 200)


class PmaxMethod(CommonMethod):

    def __init__(self, *args, **kwargs):
        super(PmaxMethod, self).__init__(*args, **kwargs)
        self.pmax = None

    def setupPmax(self, serial: str = 'A78899', account: str = '778899'):
        self.pmax = PmaxPanel(serial, account, self.connection.logger)
        self.AddMessage('Created Pmax Panel - Serial = %s, Account = %s' % (self.pmax.serial, self.pmax.account))
        self.pmax.config.host = self.connection.hostname
        return self.pmax

    def wakeUpPmax(self, panel: 'PmaxPanel', forced=False, force_p2=False):
        self.AddMessage('Enroll Pmax panel(%s) to server via %s' % (panel.config.serial, panel.config.media))
        panel.wake_up(forced=forced, force_p2=force_p2)

    def wakeUpPmaxInThread(self, panel: 'PmaxPanel', forced=False, force_p2=False):
        self.AddMessage('Wake up panel(%s) to server via %s' % (panel.config.serial, panel.config.media))
        self.thread_pmax = Thread(target=panel.wake_up, kwargs={'forced': forced, 'force_p2': force_p2})
        self.thread_pmax.start()
        time.sleep(1.5)

    def setDeviceFault(self, panel: 'PmaxPanel', fault='bypass', num = 1, type = 'detector', set = True):
        if set:
            panel.set_device_flag(name=fault, value=1, num=num, type=type)
        if set == False:
            panel.set_device_flag(name=fault, value=0, num=num, type=type)

    def setMainBoardFault(self, panel: 'PmaxPanel', fault='AcFailure', set=True):
        if set:
            setattr(panel.config.cpStatus, fault, 1)
        if set == False:
            setattr(panel.config.cpStatus, fault, 0)

    def setGSMFault(self,panel: 'PmaxPanel', fault='LineFail', set = True):
        if set:
            setattr(panel.config.gsmStatus, fault, 1)
        if set == False:
            setattr(panel.config.gsmStatus, fault, 0)

    def disconnectPmaxInThread(self, panel: 'PmaxPanel'):
        panel.config.keep_session = False
        panel.disconnect()
        if self.thread_pmax:
            self.thread_pmax.join()
        self.thread_pmax = None

    def panelLoginWithRequests(self, panel: 'PmaxPanel', client: 'RestAPIClient', type_recipient: str = 'ANDROID', mode: int = 0b1111111111):
        requests = ['get_panel_info', 'status', 'get_locations', 'get_wakeup_sms', 'register_push_recipient',
                    'get_alerts', 'get_troubles', 'get_events', 'get_all_devices', 'get_alarms']
        login = client.PanelLogin()
        self.AssertTrue(login.output, 'Client login failed', 'Client successfully login')
        self.thread_pmax = Thread(target=panel.wake_up, kwargs={'forced': False})
        self.thread_pmax.start()
        for cmd in requests:
            if cmd not in 'register_push_recipient':
                response = client.get(client.COMMANDS.get(client.version).get(cmd))
                self.ExpectTrue(response.status_code == 200, '%s response code is %s' % (cmd, response.status_code),
                                '%s response code is 200' % cmd)
            else:
                sound = 'sound3' if type_recipient == 'ANDROID' else {"0": "sound0", "1": "sound1", "default": "siren"}
                response = client.RegisterPushRecipient(token=client.token, type=type_recipient, mode=mode, version=5, sound=sound)
                self.ExpectTrue(response, '%s is %s' % (cmd, response),
                                '%s response is True' % cmd)

    def interactiveSession(self, panel: 'PmaxPanel', client: 'RestAPIClient', type_recipient: str = 'ANDROID'):
        self.SetupEmailSettings()
        self.enableUserApp(panel.serial)
        self.RegisterPowerUser(client)
        client.authenticate()
        self.LinkPanelToPowerUserIfNeeded(client, panel.serial)
        self.panelLoginWithRequests(panel, client, type_recipient)
        return client

    def enableVirtualKeypad(self, panel: 'PmaxPanel'):
        self.AddSuccess('Enable Virtual keypad')
        wb = self.initiateWebSocket()
        self.thread_pmax = Thread(target=panel.wake_up, kwargs={'forced': False})
        self.AddMessage('Wake up panel(%s) to server via %s' % (panel.config.serial, panel.config.media))
        self.thread_pmax.start()
        time.sleep(1)
        self.GuiApi.Keypad.createConnection(wb, panel.serial)
        self.pmax.VK.connect(timeout=30)
        return wb

    def genarateForAlluserCodesPmax(self, panel: 'PmaxPanel'):
        self.AddMessage('Generate user code for all user')
        for user in range(1, panel.config.MAX_SUPPORTED_DEVICE_BY_TYPE[6] + 1):
            panel.setUserCode(user, '1234')

    def disableVirtualKeypad(self, serial: str, ws: 'WebSocket'):
        self.AddSuccess('Disable Virtual keypad')
        ws.close()
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Keypad.disable(unt_id=unt_id)
        self.CheckResponseCodeStatusSuccess(response)

    def bypassHalfDetectorPmaxPanel(self, panel: 'PmaxPanel') -> int:
        self.AddMessage('Bypass half detectors')
        for detector in panel.config.devices.detector:
            if detector.number <= len(panel.config.devices.detector) // 2:
                detector.zone_bypass = 1
        quantity_bypass_detector = len([detector for detector in panel.config.devices.detector
                                        if detector.zone_bypass == 1])
        self.AddMessage('%s detector bypass is True' % quantity_bypass_detector)
        return quantity_bypass_detector

    def checkUserCodeForPmaxInPmaxUser(self, panel: 'PmaxPanel'):
        result = self.GetAllUserFromPmaxUsers(panel.serial)
        self.AssertTrue(len(result) == panel.config.MAX_SUPPORTED_DEVICE_BY_TYPE[6], 'Incorrect quantuty users in '
                        'pmax_user table - %d' % len(result), 'All user added to pmax_user table - %d' % len(result))
        for user in result:
            self.AssertTrue(user['pxu_code'] != 'NULL', 'Code for %s user not added to pmax_user' % user['pxu_panel_id'],
                            'Code for %s user added to pmax_user' % user['pxu_panel_id'])

    def checkPartitionForPmaxInPmaxUser(self, panel: 'PmaxPanel'):
        result = self.GetAllUserFromPmaxUsers(panel.serial)
        self.AssertTrue(len(result) == panel.config.MAX_SUPPORTED_DEVICE_BY_TYPE[6], 'Incorrect quantuty users in '
                        'pmax_user table - %d' % len(result), 'All user added to pmax_user table - %d' % len(result))
        for user in result:
            if user['pxu_panel_id'] == '0':
                self.AssertTrue(user['pxu_partitions'] == '1, 2, 3',
                                'Partitions not saved for user %s' % user['pxu_panel_id'],
                                'Partitions saved for user %s' % user['pxu_panel_id'])
            else:
                self.AssertTrue(user['pxu_partitions'] == '1', 'Partitions not saved for user %s' % user['pxu_panel_id'],
                                'Partitions saved for user %s' % user['pxu_panel_id'])

    def checkPermissionsForPmaxInPmaxUser(self, panel: 'PmaxPanel'):
        result = self.GetAllUserFromPmaxUsers(panel.serial)
        self.AssertTrue(len(result) == panel.config.MAX_SUPPORTED_DEVICE_BY_TYPE[6], 'Incorrect quantuty users in '
                        'pmax_user table - %d' % len(result), 'All user added to pmax_user table - %d' % len(result))
        for user in result:
            self.AssertTrue(user['pxu_permissions'] != 'NULL', 'Permissions for %s user not added to pmax_user' % user['pxu_panel_id'],
                            'Permissions for %s user added to pmax_user' % user['pxu_panel_id'])

    def getPmaxFamily(self, code) -> str:
        famalis = {
            'pro': 0x457,
            'complete': 0x550,
            'express': 0x65E,
            'powermaster-10': 0x75A,
            'powermaster-30': 0x82D,
            'powermaster-33': 0xA7D,
            'msp-2': 0xB03,
            'powermaster-360': 0xD8C,
            'powermaster360r': 0x102D,
            'powermaster-33e': 0xF8C
        }
        return list(famalis.keys())[list(famalis.values()).index(code)]

    def setEmailForUserPmax(self, pmax: 'PmaxPanel', user: int, email: str = 'test@test.com') -> bool:
        """

        :param pmax:
        :param user:  int 1,2,3,4
        :param email:
        :return:  True
        """
        self.AddMessage('Set email (%s) for user %s' % (email, user))
        pmax.config.eprom.PTable.getValue(164)[user - 1] = email.encode()
        return True

    def setEmailForAllUserPmax(self, pmax: 'PmaxPanel', email: str = 'test@test.com') -> bool:
        for user in range(1, 5):
            self.setEmailForUserPmax(pmax=pmax, user=user, email=email)
        return True

    def setPhoneForUserPmax(self, pmax: 'PmaxPanel', user: int, phone: str = '+380937788999') -> bool:
        """

        :param pmax:
        :param user:  int 1,2,3,4
        :param phone:
        :return:  True
        """
        self.AddMessage('Set email (%s) for user %s' % (phone, user))
        pmax.config.eprom.PTable.getValue(165)[user - 1] = phone.replace('+', 'B').encode()
        return True

    def setPhoneForAllUserPmax(self, pmax: 'PmaxPanel', phone: str = '+380937788999') -> bool:
        for user in range(1, 5):
            self.setPhoneForUserPmax(pmax=pmax, user=user, phone=phone)
        return True

    def AddManualPmaxPanelViaChanel(self, panel: 'PmaxPanel', module_gprs: bool, module_bb: bool,
                                    unt_sim_number: str = None, **keywords):
        self.AddMessage('Add Manual Panel %s' % panel.serial)
        modules = {True: 'offline', False: 'none'}
        self.AssertPanelWasAdded(unt_serial=panel.serial, unt_account=panel.config.account, unt_name=panel.serial,
                                 unt_sim_number=unt_sim_number, _unt_module_gprs=modules.get(module_gprs),
                                 _unt_module_bb=modules.get(module_bb), **keywords)
        self.CheckPanelOnGUI(panel.serial, True)

    def EditGroupForPanel(self, panel: PmaxPanel, group_name: str):
        self.AddMessage('Edit group for panel %s' % panel.serial)
        panelId = self.GuiApi.Units.getUnitId(panel.serial)
        group_id = self.GuiApi.Group.getGroupId(group_name)
        panel_modules = self.GetPanelInfo(panel.serial)['modules']
        bba_module = panel_modules['bba']['state'] if panel_modules['bba']['state'] else 'none'
        gprs_module = panel_modules['gprs']['state'] if panel_modules['gprs']['state'] else 'none'
        response = self.GuiApi.Units.edit(unt_id=panelId, _unt_module_gprs=gprs_module, utg_id=group_id,
                                          _unt_module_bb=bba_module, unt_serial=panel.serial,
                                          unt_account=panel.account, unt_name=panel.serial)
        self.DoCheckResponseCode(self.AssertWasSuccesfull, response, 200)
        self.DoCheckStatusSuccess(self.AssertWasSuccesfull, response, 'success')


class DscMethod(CommonMethod):

    def __init__(self, *args, **kwargs):
        super(DscMethod, self).__init__(*args, **kwargs)
        self.neo = None
        self.psp: 'NeoPanel' = None

    def setupNeoPanel(self, serial: str = 'A78899999999', account: str = '6999999999', model: str = 'HS2128', has_gsm: bool = True):
        self.neo = NeoPanel(serial, account, 'IP', logger=self.connection.logger, model=model)
        self.neo.config.host = self.connection.hostname
        self.neo.config.has_gsm = has_gsm
        self.AssertTrue(self.neo, 'NEO panel not created', 'NEO Panel - Serial = %s, Account = %s, Model = %s' %
                        (self.neo.serial, self.neo.account, self.neo.config.model))
        return self.neo

    def setupPspPanel(self, serial: str = 'A78866666666', account: str = '6555555555', model: str = 'HS3128',
                      has_gsm: bool = True):
        self.psp = NeoPanel(serial, account, 'IP', logger=self.connection.logger, model=model)
        self.psp.config.host = self.connection.hostname
        self.psp.config.itv2_sessions[3]['host'] = self.connection.hostname
        self.psp.config.has_gsm = has_gsm
        self.AssertTrue(self.psp, 'PSP panel not created', 'PSP Panel - Serial = %s, Account = %s, Model = %s' %
                        (self.psp.serial, self.psp.account, self.psp.config.model))
        return self.psp

    def setMedia(self, psp: NeoPanel, media: str):
        current_session = dict(IP=1, GSM=4).get(media, 1)
        psp.setMedia(media)
        psp.config.current_session = current_session

    def wakeUp(self, panel: 'NeoPanel'):
        self.AddMessage('Enroll panel to server via %s' % panel.config.media)
        if not self.thread or not self.thread.is_alive():
            self.AddMessage('Starting first thread')
            self.thread = Thread(target=panel.connectITv2)
            self.thread.start()
        else:
            self.AddMessage('Starting second thread')
            self.second_thread = Thread(target=panel.connectITv2)
            self.second_thread.start()
        time.sleep(4.5)

    def disconnectNeoPanel(self, panel: 'NeoPanel'):
        count_threads = lambda : len([i for i in (self.thread, self.second_thread) if i and i.isAlive()])
        self.AddMessage('Stop %s session' % panel.config.media)
        threads_number = count_threads()
        self.AddMessage('Number of alive threads: %s'%threads_number)
        panel.stopITv2Session()
        panel.config.VK.active = False
        for timer in StopWatch(5, 0.1):
            number = count_threads()
            if number == 0: break
            self.AddMessage('Number of alive threads: %s'%number)
            if number < threads_number: break
        self.waitPanelDisconnected(panel.serial)

    def disconnectDscPanel(self, panel: 'NeoPanel'):
        self.disconnectNeoPanel(panel)

    def initCommunicator(self, panel: 'NeoPanel', version: str):
        panel.config.version = version
        for i in range(4) :
            panel.config.fibroReceivers[i]['host'] = '0.0.0.0'
            panel.config.fibroReceivers[i]['hb'] = 0
        panel.config.Eprom.refresh()

    def setupReceiver(self, panel: 'NeoPanel', receiver: int, hostname=None):
        panel.config.fibroReceivers[receiver - 1]['host'] = hostname if hostname else self.connection.hostname
        port = panel.config.fibro_ports[0] if receiver in (1, 2) else panel.config.fibro_ports[1]
        panel.config.fibroReceivers[receiver - 1]['port'] = port
        self.AddMessage('Setup receiver - %s - host = %s, port = %s' % (receiver,
                                                                        panel.config.fibroReceivers[receiver - 1][
                                                                            'host'],
                                                                        panel.config.fibroReceivers[receiver - 1][
                                                                            'port']))
        panel.config.Eprom.refresh()
        panel.core.updateFibro()

    def FibroSession(self, panel: 'NeoPanel'):
        self.AddMessage("Send init and heartbeat")
        self.AddMessage(panel.sendInit())
        time.sleep(0.5)
        self.AddMessage(panel.sendHeartBeat())
        time.sleep(0.5)

    def activate_neo_panel(self, panel: 'NeoPanel'):
        time.sleep(4)
        self.AddMessage('Activate NeoPanel %s' % panel.serial)
        self.AssertTrue(self.GuiApi.Unit.ActivateNeoPanel(panel.serial), 'Panel no activated', 'Panel activated')
        self.waitNeoDiscoveryFinished(panel.serial)
        panel.waitNotificationsSent()
        self.waitNeoDiscoveryFinished(panel.serial)

    def activate_panel(self, serial: str, installer_code='5555', wait_process=True):
        time.sleep(4)
        self.CheckPanelOnGUI(serial, True)
        self.AddMessage('Activate Panel %s' % serial)
        response = self.GuiApi.Unit.ActivateNeoPanel(serial, installer_code)
        self.CheckResponseCodeStatusSuccess(response)
        if wait_process:
            prs_id = self.getProcessId(response)
            self.ExpectProcessStatusWasReached(prs_id, 'succeeded', timeout=45.00)
            return prs_id
        return self.getProcessId(response)

    def autoEnrollAndActivate(self, panel: 'NeoPanel', installer_code='5555'):
        self.AutoenrollmentForChanel('bba' if panel.config.media == 'IP' else 'gprs', True)
        self.wakeUp(panel)
        self.CheckPanelOnGUI(panel.serial, True)
        self.AddMessage('Activate Panel %s' % panel.serial)
        self.CheckResponseCodeStatusSuccess(self.GuiApi.Unit.ActivateNeoPanel(panel.serial, installer_code))

    def setFaultOnMainBoard(self, panel, fault, set=True):
        if set:
            panel.config.system_flags.troubles[fault] = 1
        else:
            panel.config.system_flags.troubles[fault] = 0

    def setFaultOnDevice(self, panel, fault, num=1, type='detector', set=True):
        if set:
            panel.set_device_trouble(trouble=fault, value=1, number=num, dev_type=type)
        else:
            panel.set_device_trouble(trouble=fault, value=0, number=num, dev_type=type)

    def setDeviceRSSILevel(self, panel, attribute, num, state):
        setattr(panel.config.devices['detector'][num], attribute, state)
        panel.config.Eprom.refreshRSSI()

    def waitPanelKeypadActive(self, panel: 'NeoPanel', timeout=10.00):
        for timer in StopWatch(timeout, 0.1):
            if panel.config.VK.active: return True
        return False

    def waitPanelKeypadInactive(self, panel: 'NeoPanel', timeout=10.00):
        for timer in StopWatch(timeout, 0.1):
            if not panel.config.VK.active: return True
        return False

    def enableVirtualKeypad(self, panel: 'NeoPanel'):
        self.AddSuccess('Enable Virtual keypad')
        ws = self.GuiApi.Keypad.createConnection(self.initiateWebSocket(), panel.serial)
        self.AssertTrue(self.waitPanelKeypadActive(panel), 'Keypad was not activated', 'Keypad was activated')
        return ws

    def disableVirtualKeypad(self, panel: 'NeoPanel', ws: 'WebSocket'):
        self.AddSuccess('Disable Virtual keypad')
        unt_id = self.GuiApi.Units.getUnitId(panel.serial)
        response = self.GuiApi.Keypad.disable(unt_id=unt_id)
        self.CheckResponseCodeStatusSuccess(response)
        ws.close()
        self.AssertTrue(self.waitPanelKeypadInactive(panel), 'Keypad was activated', 'Keypad was not activated')

    def sendArmNotification(self, panel: NeoPanel, partition: int, state: str, arm: bool = True):
        self.AddMessage('Send arm  notification state - %s' % state)
        if arm:
            panel.config.partitions[partition - 1].Arm = 1
            panel.config.partitions[partition - 1].__setattr__(state, 1)
        else:
            panel.config.partitions[partition - 1].Arm = 0
            for s in ['Stay', 'Away', 'NightArm']:
                panel.config.partitions[partition - 1].__setattr__(s, 0)
        panel.notifier.armingNotification(partition_number=partition - 1)

    def sendExitDelayNotification(self, panel: 'NeoPanel', partition: int,  status: str, duration: int = 30):
        statuses = {'Audible': 0b10000001,
                    'Restarted': 0b10000011,
                    'Urgency': 0b10000101,
                    'Silent': 0b10000000,
                    'Stopped': 0b00000000,
                    'On': 0b00000001}
        self.AddMessage('Send exit delay notification with status %s' % status)
        for delay in ['ExitDelay', 'EntryDelay', 'NoEntry']:
            if status != 'Stopped':
                panel.config.partitions[partition - 1].__setattr__(delay, 1 if delay == 'ExitDelay' else 0)
            else:
                panel.config.partitions[partition - 1].__setattr__(delay, 1 if delay == 'NoEntry' else 0)
        panel.notifier.exitDelay(partition_number=partition, status=statuses[status], duration=duration)

    def sendEntryDelayNotification(self, panel: 'NeoPanel', partition: int,  status: str, duration: int = 30):
        statuses = {'Stopped': 0x00,
                    'Normal': 0x01,
                    'UrgencyWithAlarms': 0x02,
                    'Urgency': 0x03}
        self.AddMessage('Send entry delay notification with status %s' % status)
        for delay in ['ExitDelay', 'EntryDelay', 'NoEntry']:
            if status != 'Stopped':
                panel.config.partitions[partition - 1].__setattr__(delay, 1 if delay == 'EntryDelay' else 0)
            else:
                panel.config.partitions[partition - 1].__setattr__(delay, 1 if delay == 'NoEntry' else 0)
        panel.notifier.entryDelay(partition_number=partition, status=statuses[status], duration=duration)

    def sendArmNotificationWithDelays(self, panel: 'NeoPanel', partition: int, state: str, delay: str, delay_status: str = ''):
        self.AddMessage('Arm panel state - %s, delay - %s' % (state, delay))
        self.sendArmNotification(panel, 1, state, True)
        if delay == 'ExitDelay':
            self.sendExitDelayNotification(panel, partition, delay_status)
        if delay == 'EntryDelay':
            self.sendEntryDelayNotification(panel, partition, delay_status)

    def notifyLeadInInstaller(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify Lead In Installer')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x00)

    def notifyLeadOutInstaller(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify Lead Out Installer')
        panel.core.notifier.programmingNotification(0x00, 0x01, 0x01, 0x02, 0x00)

    def notifyLeadInOutInstaller(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify LeadInOut Installer')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x00)
        panel.core.notifier.programmingNotification(0x00, 0x01, 0x01, 0x02, 0x00)

    def notifyLeadInUserMenu(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify Lead In User Menu')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x01)

    def notifyLeadOutUserMenu(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify Lead Out User Menu')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x01)

    def notifyLeadInOutUserMenu(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify LeadInOut User Menu')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x01)
        panel.core.notifier.programmingNotification(0x00, 0x01, 0x01, 0x02, 0x01)

    def sendReadyPartitionStatus(self, panel: 'NeoPanel', partition: int, ready: bool):
        self.AddMessage('Send %s status for %s partition' % ('Redy' if ready else 'Not ready', partition))
        panel.config.partitions[partition - 1].Ready = 1 if ready else 0
        panel.config.partitions[partition - 1].NotReady = 0 if ready else 1
        panel.notifier.partitionReadyStatus(partition)

    def emulateOpenRestoreZone(self, panel: 'NeoPanel', zone_number: int, status: bool):
        self.AddMessage('Emulate %s zone for %s' % ('Open' if status else 'Restore', zone_number))
        panel.config.devices.detector[zone_number].open = status
        panel.notifier.zoneOpenStatus(1)

    def waitSystemTimedeltaChanged(self, panel: 'NeoPanel', current_time: int, timeout=10, frequency=0.1):
        if panel.config.system_timedelta == current_time:
            system_timedelta = panel.config.system_timedelta
            self.AddMessage('Panel system_timeelta = %s' % system_timedelta)
            for timer in StopWatch(timeout, frequency):
                if system_timedelta != panel.config.system_timedelta:
                    self.AddSuccess('Panel system time changed - system_timedelta = %s' % panel.config.system_timedelta)
                    return
            self.AddFailure('Panel system_timedelta no changed after  %s seconds'% timeout)
            return
        else:
            self.AddSuccess('Panel system time changed - system_timedelta = %s' % panel.config.system_timedelta)

    def DoEditPanel(self, panel: 'NeoPanel', module_gprs: bool, module_bba: bool):
        modules = {True: 'offline', False: 'none'}
        self.AddMessage('Edit Panel - %s on GUI bba - %s, gprs - %s' % (panel.serial, modules.get(module_bba),
                                                                        modules.get(module_gprs)))
        panelId = self.GuiApi.Units.getUnitId(panel.serial)
        response = self.GuiApi.Units.edit(unt_id=panelId, _unt_module_gprs=modules.get(module_gprs),
                                          _unt_module_bb=modules.get(module_bba), unt_serial=panel.serial,
                                          unt_account=panel.config.system_account, unt_name=panel.serial)
        self.DoCheckResponseCode(self.AssertWasSuccesfull, response, 200)
        self.DoCheckStatusSuccess(self.AssertWasSuccesfull, response, 'success')

    def EditGroupForPanel(self, panel: 'NeoPanel', group_name: str):
        self.AddMessage('Edit group for panel %s' % panel.serial)
        self.AddMessage('Get Panel ID')
        panelId = self.GuiApi.Units.getUnitId(panel.serial)
        self.AddMessage(f"User {self.GuiApi.Login.whoami().json()}")
        self.AddMessage(f"Panel ID {panelId}")
        self.AddMessage('Get Group ID')
        group_id = self.GuiApi.Group.getGroupId(group_name)
        self.AddMessage(f"Group ID {group_id}")
        panel_modules = self.GetPanelInfo(panel.serial)['modules']
        bba_module = panel_modules['bba']['state']
        gprs_module = panel_modules['bba']['state']
        if not bba_module or bba_module != 'online':
            bba_module = 'offline'
        if not gprs_module or gprs_module != 'online':
            gprs_module = 'offline'
        response = self.GuiApi.Units.edit(unt_id=panelId,
                                          _unt_module_gprs=str(gprs_module).lower(),
                                          utg_id=group_id,
                                          _unt_module_bb=str(bba_module).lower(),
                                          unt_serial=panel.serial,
                                          unt_account=panel.config.system_account,
                                          unt_name=panel.serial)
        self.DoCheckResponseCode(self.AssertWasSuccesfull, response, 200)
        self.DoCheckStatusSuccess(self.AssertWasSuccesfull, response, 'success')

    def GenerateAlarm(self, panel: 'NeoPanel', alarm='PA'):
        self.AddMessage('Generate %s alarm' % alarm)
        return panel.sendSiaEvent(alarm, 1)

    def AddManualPanelViaChanel(self, panel: 'NeoPanel',  module_gprs: bool, module_bb: bool,
                                unt_sim_number: str = None, **keywords):
        modules = {True: 'offline', False: 'none'}
        self.AssertPanelWasAdded(unt_serial=panel.serial, unt_account=panel.config.system_account,
                                 unt_name=panel.serial, unt_sim_number=unt_sim_number,
                                 _unt_module_gprs=modules.get(module_gprs), _unt_module_bb=modules.get(module_bb),
                                 **keywords)
        self.CheckPanelOnGUI(panel.serial, True)

    def GenerateForAllUserCodes(self,panel: 'NeoPanel', length=4):
        max_code = '12345678'
        for user in panel.config.users:
            code = max_code[:length]
            user.code = code

    def setDisabelBypassAvailabilityForHalfDetectors(self, panel: 'NeoPanel'):
        self.AddMessage('Set disabled bypass_enabled for %s detector' % str(len(panel.config.devices.detector) // 2))
        for detector in panel.config.devices.detector:
            if detector.number in range((len(panel.config.devices.detector) // 2) + 1):
                detector.attributes = 0

    def getQuantityDetectoEnabledBypassDisabledAndEnabled(self, panel: 'NeoPanel') -> dict:
        quantity_enabled = 0
        quantity_disabled = 0
        for detector in panel.config.devices.detector:
            if detector.attributes:
                quantity_enabled += 1
            else:
                quantity_disabled += 1
        return {'enabled': quantity_enabled, 'disabled': quantity_disabled}

    def addMaxOutputExpanderForAllPartition(self, panel: 'NeoPanel') -> int:
        partition_bit_mask = (1 << MODELS[panel.config.model]['partition']) - 1
        for number in range(1, MODELS[panel.config.model]['output_expander'] + 1):
            panel.add_device('OUTPUT_EXPANDER', 0)
            panel.config.devices.output_expander[number].partition = partition_bit_mask

    def addMaxPanicButton1(self, panel: 'NeoPanel'):
        self.AddMessage('Add %s panic button 1' % MODELS[panel.config.model]['detector'])
        for number in range(1, MODELS[panel.config.model]['detector'] + 1):
            panel.add_device('PENDANT_PANIC_101', 0)
        quantity = len([detector for detector in panel.config.devices.detector if detector.name == 'pendant_panic_101'])
        self.AddMessage(' Added %s Panic button 1' % quantity)
        return quantity

    def addMaxPanicButton2(self, panel: 'NeoPanel'):
        self.AddMessage('Add %s panic button 2' % MODELS[panel.config.model]['keyfob'])
        for number in range(1, MODELS[panel.config.model]['keyfob'] + 1):
            panel.add_device('PENDANT_PANIC_102', 0)
        quantity = len([keyfob for keyfob in panel.config.devices.keyfob if keyfob.name == 'pendant_panic_102'])
        self.AddMessage(' Added %s Panic button 2' % quantity)
        return quantity

    def addMaxKeyfobsForNeoPanel(self, panel: 'NeoPanel'):
        self.AddMessage('Add %s KEYFOB' % MODELS[panel.config.model]['keyfob'])
        for number in range(1, MODELS[panel.config.model]['keyfob'] + 1):
            panel.add_device('KEYFOB', 0)
        quantity = len([keyfob for keyfob in panel.config.devices.keyfob if keyfob.name == 'pendant_panic_102'])
        self.AddMessage(' Added %s KEYFOB' % quantity)
        return quantity

    def addMaxTypeDeviceToPanel(self, panel: 'NeoPanel', device: str):
        max_type = panel.config.devices.get_table(DeviceType[device][0].lower())._size
        # max_type = MODELS[panel.config.model][DeviceType[device][0].lower()]
        self.AddMessage('Add %s %s' % (max_type, device))
        for number in range(1, max_type + 1):
            panel.add_device(device, 0)
        dev_type = DeviceType[device][0].lower()
        quantity = panel.config.devices.getMaxDevices(dev_type)
        self.AddMessage(' Added %s %s' % (quantity, device))
        return quantity

    def setPgmTypeForFourPGM(self, panel: 'NeoPanel'):
        partition_bit_mask = (1 << MODELS[panel.config.model]['partition']) - 1
        type = ['Output 1', 'Output 2', 'Output 3', 'Output 4']
        for pgm in range(1, 5):
            panel.config.devices.pgm[pgm].setType(type[pgm - 1])
            panel.config.devices.pgm[pgm].partition = partition_bit_mask

    def quantityComandOutputs(self, panel: NeoPanel):
        comand_outputs = 0
        type = ['Output 1', 'Output 2', 'Output 3', 'Output 4']
        for pgm in panel.config.devices.pgm:
            if pgm.type in type:
                comand_outputs += bin(pgm.partition)[2:].count('1')
        return comand_outputs

    def bypassHalfDetector(self, panel: 'NeoPanel') -> int:
        self.AddMessage('Bypass half detectors')
        for detector in panel.config.devices.detector:
            if detector.number <= len(panel.config.devices.detector) // 2:
                detector.bypass = True
        quantity_bypass_detector = len([detector for detector in panel.config.devices.detector if detector.bypass])
        self.AddMessage('%s detector bypass is True' % quantity_bypass_detector)
        return quantity_bypass_detector

    def getCountTroubleDetectors(self, panel: 'NeoPanel') -> int:
        count = 0
        for detector in panel.config.devices.detector:
            for trouble, value in detector.troubles.items():
                if value == 1:
                    count += 1
        return count

    def addTamperTroubleToAllDetector(self, panel: 'NeoPanel'):
        self.AddMessage('Add Tamper trouble to all detector')
        for detector in panel.config.devices.detector:
            detector.troubles['tamper'] = 1
        troubles = self.getCountTroubleDetectors(panel)
        self.AddMessage('Added %s troubles to detector' % troubles)

    def notifyExitInstaller(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify exit Installer')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x00)
        panel.core.notifier.programmingNotification(0x00, 0x01, 0x01, 0x02, 0x00)

    def notifyExitUserMenu(self, panel: 'NeoPanel'):
        self.AddMessage('Send notify exit User Menu')
        panel.core.notifier.programmingNotification(0x00, 0x00, 0x01, 0x02, 0x01)
        panel.core.notifier.programmingNotification(0x00, 0x01, 0x01, 0x02, 0x01)

    def interruptAndRestoreFreeDiscoveryAfterEachStage(self, panel: 'NeoPanel'):
        all_discovery = list(free_neo_discovery_stages) if panel.config.model_type == 'neo' else list(free_psp_discovery_stages)
        if panel.config.model_type == 'psp':
            if panel.config.media == 'IP':
                all_discovery.remove('discovery_change_integration_access_code_gprs')
            else:
                all_discovery.remove('discovery_change_integration_access_code_bba')
        for discovery in all_discovery:
            if discovery==all_discovery[0]:
                self.waitDiscoveryStageAppearedInRedis(panel.serial, discovery)
            self.waitDiscoveryStage(panel.serial, discovery)
            self.disconnectNeoPanel(panel)
            self.wakeUp(panel)

    def interruptAndRestoreDiscoveryAfterEachStage(self, panel: 'NeoPanel', discovery_stage: str):
        panel.config.resp_timeout = 0.5
        self.wakeUp(panel)
        self.activate_panel(panel.config.serial, wait_process=False)
        self.waitDiscoveryStageAppearedInRedis(panel.serial, discovery_stage, timeout=60.00)
        self.waitDiscoveryStage(panel.serial, discovery_stage, timeout=420)
        self.disconnectNeoPanel(panel)
        panel.config.resp_timeout = 0.01
        self.wakeUp(panel)
        panel_info = self.GetPanelInfo(panel.serial)
        if panel_info['unt_activated'] == '0':
            self.AddMessage('Panel not activated, Panel is activated again')
            self.activate_panel(panel.config.serial)
        all_discovery_stages = list(all_neo_discovery_stages) if panel.config.model_type == 'neo' else list(all_psp_discovery_stages)
        if panel.config.model_type == 'psp':
            if panel.config.media == 'IP':
                all_discovery_stages.remove('discovery_change_integration_access_code_gprs')
            else:
                all_discovery_stages.remove('discovery_change_integration_access_code_bba')
        self.waitDiscoveryStagesCheckInRedis(panel.serial, all_discovery_stages)

    def CheckFreeDiscoveryStagesInRedisPSP(self, panel: 'NeoPanel'):
        self.AddMessage('Check Free Discovery stages in Redis')
        all_free_discovery = list(free_psp_discovery_stages)
        if panel.config.model_type == 'psp':
            if panel.config.media == 'IP':
                all_free_discovery.remove('discovery_change_integration_access_code_gprs')
            else:
                all_free_discovery.remove('discovery_change_integration_access_code_bba')
        for name in all_free_discovery:
            if name==all_free_discovery[0]:
                self.waitDiscoveryStageAppearedInRedis(panel.serial, name)
            self.waitDiscoveryStage(panel.config.serial, name)

    def getAllDiscoveryForPsp(self, panel: 'NeoPanel') -> list:
        all_discovery = list(all_psp_discovery_stages)
        if panel.config.media == 'IP':
            all_discovery.remove('discovery_change_integration_access_code_gprs')
        else:
            all_discovery.remove('discovery_change_integration_access_code_bba')
        return all_discovery

    def enabledAllPartition(self, panel: NeoPanel):
        self.AddMessage('Enabled All partition for panel')
        for partition in panel.config.partitions:
            partition.enabled = True

    def panelLoginWithRequests(self, panel: 'NeoPanel', client: 'RestAPIClient', type_recipient: str = 'ANDROID',
                               wake_up: bool = True , mode: int = 0b1111111111):
        requests = ['get_panel_info', 'status', 'get_locations', 'get_wakeup_sms', 'register_push_recipient',
                    'get_alerts', 'get_troubles', 'get_events', 'get_all_devices', 'get_alarms']
        login = client.PanelLogin()
        self.AssertTrue(login.output, 'Client login failed', 'Client successfully login')
        if wake_up: self.wakeUp(panel)
        for cmd in requests:
            if cmd not in 'register_push_recipient':
                response = client.get(client.COMMANDS.get(client.version).get(cmd))
                self.ExpectTrue(response.status_code == 200, '%s response code is %s' % (cmd, response.status_code),
                                '%s response code is 200' % cmd)
            else:
                sound = 'sound3' if type_recipient == 'ANDROID' else {"0": "sound0", "1": "sound1", "default": "siren"}
                response = client.RegisterPushRecipient(token=client.token, type=type_recipient, mode=mode, version=5, sound=sound)
                self.ExpectTrue(response, '%s is %s' % (cmd, response),
                                '%s response is True' % cmd)

    def interactiveSession(self, panel: 'NeoPanel', client: 'RestAPIClient', type_recipient: str = 'ANDROID'):
        self.SetupEmailSettings()
        self.enableUserApp(panel.serial)
        self.RegisterPowerUser(client)
        client.authenticate()
        self.LinkPanelToPowerUserIfNeeded(client, panel.serial)
        self.panelLoginWithRequests(panel, client, type_recipient)
        return client

    def startRSSIPspPanel(self, prs_id, panel: 'NeoPanel'):
        self.dls = DlsConnectionTask(panel, delay=0.5)
        self.dls.start()
        self.AssertLoginWasSuccess()
        self.waitProcessStatus(prs_id, 'succeeded')
        self.dls.stopTask()
        self.dls.join()


class DualPath(CommonMethod):

    def __init__(self, *args, **kwargs):
        super(DualPath, self).__init__(*args, **kwargs)
        self.dual_path = None

    def setupDualPath(self, serial: str = 'BGS_1234567A', media: str = 'GSM'):
        self.dual_path = DualPathCommunicator(serial=serial, media=media, logger=self.connection.logger)
        self.dual_path.config.host = self.connection.hostname
        self.AssertTrue(self.dual_path, 'DualPath panel not created', 'DualPath Panel - Serial = %s Media - %s' %
                        (serial, media))
        return self.dual_path

    def wakeUpDualPath(self, panel: 'DualPathCommunicator'):
        self.AddMessage('Enroll panel to server via %s' % panel.config.media)
        if not self.thread or not self.thread.is_alive():
            self.thread = Thread(target=panel.connectITv2)
            self.thread.start()
        else:
            self.second_thread = Thread(target=panel.connectITv2)
            self.second_thread.start()
        time.sleep(4.5)

    def change_media(self, panel: 'DualPathCommunicator', media):
        self.AddMessage('Change media from {} to {}'.format(panel.config.media, media))
        panel.config.media = media

    def disconnectDualPathPanel(self, panel: 'DualPathCommunicator'):
        self.AddMessage('Stop %s session' % panel.config.media)
        panel.stopITv2Session()
        if self.thread and not self.thread.is_alive():
            self.thread.join()
            self.thread = None
        if self.second_thread and not self.second_thread.is_alive():
            self.second_thread.join()
            self.second_thread = None
        self.waitPanelDisconnected(panel.serial_number)

    def panelLoginWithRequests(self, panel: 'DualPathCommunicator', client: 'RestAPIClient',
                               type_recipient: str = 'ANDROID', mode: int = 0b1111111111):
        requests = ['get_panel_info', 'status', 'get_locations', 'get_wakeup_sms', 'register_push_recipient',
                    'get_alerts', 'get_troubles', 'get_events', 'get_all_devices', 'get_alarms']
        login = client.PanelLogin()
        self.AssertTrue(login.output, 'Client login failed', 'Client successfully login')
        for cmd in requests:
            if cmd not in 'register_push_recipient':
                response = client.get(client.COMMANDS.get(client.version).get(cmd))
                self.ExpectTrue(response.status_code == 200, '%s response code is %s' % (cmd, response.status_code),
                                '%s response code is 200' % cmd)
            else:
                sound = 'sound3' if type_recipient == 'ANDROID' else {"0": "sound0", "1": "sound1", "default": "siren"}
                response = client.RegisterPushRecipient(token=client.token, type=type_recipient, mode=mode, version=5, sound=sound)
                self.ExpectTrue(response, '%s is %s' % (cmd, response),
                                '%s response is True' % cmd)