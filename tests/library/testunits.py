#*************************************************************************
#**** IMPORT :: SYSTEM ***************************************************
#*************************************************************************
import json
import random
import re
import string
from io import BytesIO
from threading import Thread

import magic
from PIL import Image
from simplejson import JSONDecodeError

import atl.trackable as trackable
import atl.utils.sequences as sequences
# import ipmp.pages as automation
import testcase
from atl.utils.stopwatch import StopWatch
from autolib import JenkinsTestCase
from ipmp.email_reader import IMAPClient
from ipmp.emu.pmax import PmaxPanel
from ipmp.interactive.rest.client import RestAPIClient, RestInstaller
from ipmp.pages import GuiApi, Status
from ipmp.setup import IpmpInitalSetup


class TestList(testcase.TestList) : pass




#*************************************************************************
#**** TEST :: RUNNER *****************************************************
#*************************************************************************
class TestRunner(testcase.TestRunner) :



    def __init__( self, location ) :
        #create instance of the output
        logger = trackable.Logger(location,'DEBUG')
        format = trackable.Formatter('%(levelname)s>>>%(message)s')
        target = trackable.StreamHandler()
        target . setFormatter(format)
        logger . addHandler(target)
        format = trackable.HtmlFormatter()
        target = trackable.FileHandler(location,'w','utf-8',True)
        target . setFormatter(format)
        logger . addHandler(target)
        self.output = testcase.TestOutputLogger(logger)
        #initialize basic class
        super(TestRunner,self).__init__(self.output)

    def Results(self):
        return self.output.Results()

#*************************************************************************
#**** TEST :: EXTENDED METHODS *******************************************
#*************************************************************************
class ExtendedMethods(object) :

    
    def DoCheckResponseCode(self, verificator, response, expected):
        result = response.status_code==expected
        message = 'Status code is %s' %response.status_code
        return verificator(result, message, message)
        
    def ExpectResponseCode(self, response, expected): return self.DoCheckResponseCode(self.ExpectWasSuccesfull, response, expected)
    def AssertResponseCode(self, response, expected): return self.DoCheckResponseCode(self.AssertWasSuccesfull, response, expected)
    
    def DoCheckStatusSuccess(self, verificator, response, status):
        try:
            data = response.json()
            self.AddMessage('Response json is: "%s"'%json.dumps(data))
            result = data['status']==status
            message = 'Response status is "%s"'%data['status']
            return verificator(result, message, message)
        except JSONDecodeError:
            self.AddFailure('Empty data in response for %s request. Status %s. Text: "%s"' % (response.request.url, response.status_code, response.text))
            return False
        
    def AssertResponseStatusSuccess(self, response, status): return self.DoCheckStatusSuccess(self.AssertWasSuccesfull, response, status)
    def ExpectResponseStatusSuccess(self, response, status): return self.DoCheckStatusSuccess(self.ExpectWasSuccesfull, response, status)
    
    def CheckResponseCodeStatusSuccess(self, response, exp_code=200, status='success'):
        self.AddMessage('Request - url: %s, body: %s' % (response.request.url, response.request.body))
        self.ExpectResponseStatusSuccess(response, status)
        self.AssertResponseCode(response, exp_code)
        
    def DoCheckLoginSuccess(self, verificator, usr_email=None, usr_password=None):
        if usr_email is None: usr_email=self.web.email
        if usr_password is None: usr_password=self.web.password
        self.AddMessage("Login to %s (%s, %s)" % (self.connection.hostname, usr_email, usr_password))
        login = self.GuiApi.Login.login(usr_email=usr_email, usr_password=usr_password)
        message = 'Status code is %s'%login.status_code
        result = verificator(login, message, message)
        return login
    
    def AssertLoginWasSuccess(self, usr_email=None, usr_password=None): return self.DoCheckLoginSuccess(self.AssertWasSuccesfull, usr_email=usr_email, usr_password=usr_password)
    def AssertLoginNotSuccess(self, usr_email=None, usr_password=None): return self.DoCheckLoginSuccess(self.AssertNotSuccesfull, usr_email=usr_email, usr_password=usr_password)
    def ExpectLoginWasSuccess(self, usr_email=None, usr_password=None): return self.DoCheckLoginSuccess(self.ExpectWasSuccesfull, usr_email=usr_email, usr_password=usr_password)
    def ExpectLoginNotSuccess(self, usr_email=None, usr_password=None): return self.DoCheckLoginSuccess(self.ExpectNotSuccesfull, usr_email=usr_email, usr_password=usr_password)
    
    def Login(self, usr_email=None, usr_password=None):
        return self.AssertLoginWasSuccess(usr_email=usr_email, usr_password=usr_password)

    def DoCheckResponseMessage(self, verificator, response, message):
        data = response.json()
        result = data['message']== message
        response_message = 'Response message is: "%s"'%data['message']
        return verificator(result, response_message, response_message)

    def AssertResponseMessage(self, response, status): return self.DoCheckResponseMessage(self.AssertWasSuccesfull, response, status)
    def ExpectResponseMessage(self, response, status): return self.DoCheckResponseMessage(self.ExpectWasSuccesfull, response, status)

    def DoCheckResponseCount(self, verificator, response, count=None):
        data = response.json()['data']['rows']
        counter = 0
        for e in data:
            if u'evt_id' in e: counter+=1
        if count and count<=counter: result = True
        else: result = counter != 0
        message = "Quantity is %s"%counter
        return verificator(result, message, message)

    def AssertResponseCount(self, response, count=None): return self.DoCheckResponseCount(self.AssertWasSuccesfull, response, count)
    def ExpectResponseCount(self, response, count=None): return self.DoCheckResponseCount(self.ExpectWasSuccesfull, response, count)
    def AssertResponseCountNone(self, response, count=None): return self.DoCheckResponseCount(self.AssertNotSuccesfull, response, count)
    def ExpectResponseCountNone(self, response, count=None): return self.DoCheckResponseCount(self.ExpectNotSuccesfull, response, count)
    
    def StartRSSITest(self, untID, status_code, status):
        self.AddMessage('Starting RSSI test for unit id "%s"'%untID)
        response = self.GuiApi.Diagnostic.startRSSI(unt_id=untID)
        self.CheckResponseCodeStatusSuccess(response, exp_code=status_code, status=status)
        return response.json()
    
    def DoCheckFaults(self, verificator, response):
        data = response.json()['data']['rows']
        for e in data:
            if e[u'unt_serial']:
                result = e[u'faults'] != []
                message_s = 'Panel %s has fault(s)' %(e[u'unt_serial'])
                message_f = 'Panel %s doesn`t have fault(s)' % (e[u'unt_serial'])
                verificator(result, message_f, message_s)

    def AssertResponseFaults(self, response): return self.DoCheckFaults(self.AssertWasSuccesfull, response)
    def ExpectResponseFaults(self, response): return self.DoCheckFaults(self.ExpectWasSuccesfull, response)
    def AssertResponseFaultsNone(self, response): return self.DoCheckFaults(self.AssertNotSuccesfull, response)
    def ExpectResponseFaultsNone(self, response): return self.DoCheckFaults(self.ExpectNotSuccesfull, response)

    def DoCheckUnitDevices(self, verificator, response, subtype='MOTION_CAMERA'):
        data = response.json()['data']['devices']
        devices = 0
        for e in data:
            if u'id' in e and e['subtype']==subtype:
                devices +=1
        result = devices !=0
        message = "Panel have %s devices (%s(s))" %(devices, subtype)
        return verificator(result, message, message)

    def AssertResponseCountDevices(self, response): return self.DoCheckUnitDevices(self.AssertWasSuccesfull, response)
    def ExpectResponseCountDevices(self, response, subtype='MOTION_CAMERA'): return self.DoCheckUnitDevices(self.ExpectWasSuccesfull, response, subtype)
    def AssertResponseCountDevicesNone(self, response): return self.DoCheckUnitDevices(self.AssertNotSuccesfull, response)
    def ExpectResponseCountDevicesNone(self, response): return self.DoCheckUnitDevices(self.ExpectNotSuccesfull, response)

    def DoCheckEventCameras(self, verificator, response):
        data = response.json()['data']['event']
        cameras =0
        if data:
            for e in data:
                if u'eti_camera_id' in e: cameras +=1
        result = cameras != 0
        message = '%s cameras related to a given event'%cameras
        return verificator(result, message, message)

    def AssertResponseCountCameras(self, response): return self.DoCheckEventCameras(self.AssertWasSuccesfull, response)
    def ExpectResponseCountCameras(self, response): return self.DoCheckEventCameras(self.ExpectWasSuccesfull, response)
    def AssertResponseCountCamerasNone(self, response): return self.DoCheckEventCameras(self.AssertNotSuccesfull, response)
    def ExpectResponseCountCamerasNone(self, response): return self.DoCheckEventCameras(self.ExpectNotSuccesfull, response)

    # def DoCheckSuggestionsCount(self, verificator, response):
    #     data = response.json()['data']
    #     suggest = 0
    #     if data:
    #         for e in data['evt_id']['rows']:
    #             if u'suggest' in e:suggest +=1
    #     result = suggest !=0
    #     message = '%s suggestion for the given field' %suggest
    #     return verificator(result, message, message)

    def AssertResponseCountSuggestions(self, response, filter='unt_id'): return self.DoCheckSuggestions(self.AssertWasSuccesfull, response, filter)
    def ExpectResponseCountSuggestions(self, response, filter='unt_id'): return self.DoCheckSuggestions(self.ExpectWasSuccesfull, response, filter)
    def AssertResponseCountSuggestionsNone(self, response, filter='unt_id'): return self.DoCheckSuggestions(self.AssertNotSuccesfull, response, filter)
    def ExpectResponseCountSuggestionsNone(self, response, filter='unt_id'): return self.DoCheckSuggestions(self.ExpectNotSuccesfull, response, filter)

    def DoCheckSuggestions(self, verificator, response, filter):
        data = response.json()['data'][filter]
        suggestion = 0
        for e in data['rows']:
            if u'suggest' in e: suggestion +=1
        result = suggestion >= 0
        message = '%s suggestion for the given field' % suggestion
        return verificator(result, message, message)

    def DoCheckEventFootage(self, verificator, response):
        data = response.json()['data']
        preloaded = 0
        live = 0
        if data:
            for e in data['preloaded']:
                if e[u'frames']: preloaded +=1
            for e in data['live']:
                if e[u'frames']: live += 1
        result = preloaded + live != 0
        message = 'Event have %s preloaded frames and %s live frames' % (preloaded, live)
        return verificator(result, message, message)

    def AssertResponseCountFrames(self, response): return self.DoCheckEventFootage(self.AssertWasSuccesfull, response)
    def ExpectResponseCountFrames(self, response): return self.DoCheckEventFootage(self.ExpectWasSuccesfull, response)
    def AssertResponseCountFramesNone(self, response): return self.DoCheckEventFootage(self.AssertNotSuccesfull, response)
    def ExpectResponseCountFramesNone(self, response): return self.DoCheckEventFootage(self.ExpectNotSuccesfull, response)

    def DoCheckLiveFrames(self, verificator, response):
        data = response.json()['data']['videodata']
        frames = 0
        for e in data:
            if e[u'frames']: frames +=1
        result = frames >=0
        message = 'Event have %s live frames' %frames
        return verificator(result, message, message)

    def AssertResponseCountLiveFrames(self, response): return self.DoCheckLiveFrames(self.AssertWasSuccesfull, response)
    def ExpectResponseCountLiveFrames(self, response): return self.DoCheckLiveFrames(self.ExpectWasSuccesfull, response)
    def AssertResponseCountLiveFramesNone(self, response): return self.DoCheckLiveFrames(self.AssertNotSuccesfull, response)
    def ExpectResponseCountLiveFramesNone(self, response): return self.DoCheckLiveFrames(self.ExpectNotSuccesfull, response)

    def DoCheckLanguages(self, verificator, response):
        data = response.json()['data']['rows']
        languages = 0
        name = []
        for e in data:
            if u'ugl_short' in e:
                languages +=1
                name.append(e[u'ugl_short'])
        result = languages != 0
        message = 'Language(s) %s (%s)' %(languages, name)
        return verificator(result, message, message)
    
    def DoAddPanel(self, verificator, unt_serial='A1234567890F', unt_name='A1234567890F', unt_account='654321', utg_id=1, **keywords):
        self.AddMessage('Adding panel: serial - "%s", webname - "%s", account - "%s"'%(unt_serial, unt_name, unt_account))
        vendors = {12: 'NEO', 6: 'POWER_MASTER', 8: 'DUAL_PATH'}
        response = self.GuiApi.Units.add(unt_serial=unt_serial, unt_name=unt_name, unt_account=unt_account, utg_id=utg_id, vendor=vendors.get(len(unt_serial)), **keywords)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')
        
    def ExpectPanelWasAdded(self, unt_serial='A1234567890F', unt_name='A1234567890F', unt_account='654321', utg_id=1, **keywords): self.DoAddPanel(self.ExpectWasSuccesfull, unt_serial=unt_serial, unt_name=unt_name, unt_account=unt_account, utg_id=utg_id, **keywords)
    def AssertPanelWasAdded(self, unt_serial='A1234567890F', unt_name='A1234567890F', unt_account='654321', utg_id=1, **keywords): self.DoAddPanel(self.AssertWasSuccesfull, unt_serial=unt_serial, unt_name=unt_name, unt_account=unt_account, utg_id=utg_id, **keywords)

    def waitPanelIsAbsent(self, serial, timeout=10, frequency=0.1):
        # todo: self.ExpectProcessWasSucceeded(prs_id)
        for timer in StopWatch(timeout, frequency):
            panelId = self.GuiApi.Units.getUnitId(serial)
            if not panelId:
                self.AddSuccess('Panel "%s" is absent on server'%serial)
                return
        self.AddFailure('Panel "%s" is still present on server after "%s" seconds'%(serial, timeout))

    def DoAddDevice(self, verificator, serial, zoneId = 1, deviceId = 1000001, partitions = [1]):
        self.AddMessage('Adding device {} with zone id {}'.format(deviceId, zoneId))
        unt_id = self.GuiApi.Units.getUnitId(serial)
        response = self.GuiApi.Diagnostic.add(unt_id=unt_id, zoneId=zoneId, deviceId=deviceId, partitions=partitions)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')

    def AssertDeviceWasAddedPreenroll(self, serial, zoneId, deviceId, partitions): self.DoAddDevice(self.AssertWasSuccesfull, serial, zoneId, deviceId, partitions)

    def getProcessId(self, response):
        return response.json()['data']['prs_id']
        
    
    def getPrsIds(self, response):
        batch_id = response.json()['data']['id']
        prs_ids = self.GuiApi.Runners.waitProcessIds(batch_id)
        self.AssertTrue(all(prs_ids), 'Not all processes were started')
        return prs_ids
    
    def getPrsId(self, response) :
        batch_id = response.json()['data']['id']
        prs_ids = self.GuiApi.Runners.waitProcessIds(batch_id)
        self.AssertTrue(all(prs_ids), 'Not all processes were started')
        return prs_ids[0]

    def getRunnerPrsId(self, response) :
        runner_id = response.json()['data']['runner_id']
        prs_id = self.GuiApi.Runners.wait_prs_id_from_runner(runner_id)
        self.AssertTrue(prs_id, 'Process was not started')
        return prs_id

    def DoRemovePanel(self, verificator, serial):
        self.AddMessage('Removing panel "%s"'%serial)
        response = self.GuiApi.Units.removeUnit(serial)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')
        self.waitPanelIsAbsent(serial, 10)
        
    def ExpectPanelWasRemoved(self, serial): self.DoRemovePanel(self.ExpectWasSuccesfull, serial)
    def AssertPanelWasRemoved(self, serial): self.DoRemovePanel(self.AssertWasSuccesfull, serial)

    def DoRemovePmaxPanel(self, verificator, panel: 'PmaxPanel'):
        self.AddMessage('Removing panel "%s"' % panel.serial)
        response = self.GuiApi.Units.removeUnit(panel.serial)
        prs_id = self.getPrsIds(response)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')
        thread = Thread(target=panel.wake_up)
        thread.start()
        self.GuiApi.Processes.waitProcessNotInStatus(prs_id, 'Succeeded')
        self.waitPanelIsAbsent(panel.serial)
        panel.disconnect()
        thread.join()

    def ExpectPmaxPanelWasRemoved(self,  panel: 'PmaxPanel'): self.DoRemovePmaxPanel(self.ExpectWasSuccesfull, panel)
    def AssertPmaxPanelWasRemoved(self,  panel: 'PmaxPanel'): self.DoRemovePmaxPanel(self.AssertWasSuccesfull, panel)

    def DoRemovePanelsIfNeeded(self, verificator, serial: list):
        self.AddMessage('Remove panels: %s'%serial)
        response = self.GuiApi.Units.removeUnits(serial)
        if not isinstance(response, bool):
            self.DoCheckResponseCode(verificator, response, 200)
            self.DoCheckStatusSuccess(verificator, response, 'success')
        for s in serial:
            self.waitPanelIsAbsent(s, 10)
    
    def RemoveAllPanels(self, count=15):
        self.AddMessage('Remove all units with count %s'%count)
        response = self.GuiApi.Units.removeAllUnits(count=count)
        if isinstance(response, bool) and response==True:
            self.AddSuccess('No units on panels page')
            return
        self.CheckResponseCodeStatusSuccess(response, 200, 'success')
        units = list()
        for timer in StopWatch(30.00, 0.3):
            units = self.GuiApi.Units.getUnits(count=count)
            if not units: self.AddSuccess('All units were removed')
            return
        else:
            self.AddFailure('Not all units were removed. List of units remained:')
            for unit in units:
                self.AddMessage(str(unit))
            
        

    def ExpectPanelWasRemovedIfNeeded(self, serials: list):
        self.DoRemovePanelsIfNeeded(self.ExpectWasSuccesfull, serials)

    def AssertPanelWasRemovedIfNeeded(self, serials: list):
        self.DoRemovePanelsIfNeeded(self.AssertWasSuccesfull, serials)

    def DoAddGroup(self, verificator, name, **keywords):
        self.AddMessage('Adding group with name "%s"'%name)
        response = self.GuiApi.Group.create(name=name, **keywords)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')
    
    def ExpectGroupWasAdded(self, name, **keywords): return self.DoAddGroup(self.ExpectWasSuccesfull, name, **keywords)
    def ExpectGroupNotAdded(self, name, **keywords): return self.DoAddGroup(self.ExpectNotSuccesfull, name, **keywords)
    def AssertGroupNotAdded(self, name, **keywords): return self.DoAddGroup(self.AssertNotSuccesfull, name, **keywords)
    def AssertGroupWasAdded(self, name, **keywords): return self.DoAddGroup(self.AssertWasSuccesfull, name, **keywords)

    def DoEditGroup(self, verificator, name, **keywords):
        self.AddMessage('Edit group with name "%s"' % name)
        response = self.GuiApi.Group.editGroup(name=name, **keywords)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')

    def ExpectGroupWasEdited(self, name, **keywords): return self.DoEditGroup(self.ExpectWasSuccesfull, name, **keywords)
    def AssertGroupWasEdited(self, name, **keywords): return self.DoEditGroup(self.AssertWasSuccesfull, name, **keywords)
    
    def DoRemoveGroups(self, verificator, names):
        self.AddMessage('Remove groups %s'%names)
        ids = self.GuiApi.Group.getGroupIds(names)
        response = self.GuiApi.Group.remove(groupIds=ids)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')
        
    def ExpectGroupsWasRemoved(self, names): return self.DoRemoveGroups(self.ExpectWasSuccesfull, names)
    
    
    def DoAddCS(self, verificator, name, **keywords):
        self.AddMessage('Adding CS with name "%s"'%name)
        response = self.GuiApi.CentralStations.addStation(name=name, **keywords)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')
        
    def ExpectCSWasAdded(self, name, **keywords): return self.DoAddCS(self.ExpectWasSuccesfull, name, **keywords)
    def ExpectCSNotAdded(self, name, **keywords): return self.DoAddCS(self.ExpectWasSuccesfull, name, **keywords)
    def AssertCSNotAdded(self, name, **keywords): return self.DoAddCS(self.AssertNotSuccesfull, name, **keywords)
    def AssertCSWasAdded(self, name, **keywords): return self.DoAddCS(self.AssertWasSuccesfull, name, **keywords)

    def DoEditCS(self, verificator, name, **keywords):
        self.AddMessage('Edit CS with name "%s"' % name)
        response = self.GuiApi.CentralStations.editStation(name=name, **keywords)
        self.DoCheckResponseCode(verificator, response, 200)
        self.DoCheckStatusSuccess(verificator, response, 'success')

    def ExpectCSWasEdited(self, name, **keywords): return self.DoEditCS(self.ExpectWasSuccesfull, name, **keywords)
    def AssertCSWasEdited(self, name, **keywords): return self.DoEditCS(self.AssertWasSuccesfull, name, **keywords)

    def DoRemoveCentralStations(self, verificator, names):
        self.AddMessage('Removing central stations with names %s'%names)
        result = self.GuiApi.CentralStations.removeStations(names)
        failure = 'Could not remove stations'
        success = 'Stations was removed'
        return verificator(result, failure, success)
    
    def ExpectCentralStationsWasRemoved(self, names): return self.DoRemoveCentralStations(self.ExpectWasSuccesfull, names)
    def AssertCentralStationsWasRemoved(self, names): return self.DoRemoveCentralStations(self.AssertWasSuccesfull, names)
    
    def DoAddCSLink(self, group_name, cs_name, profiles):
        '''
        Add CS link to group with profiles
        :param group_name: name of group
        :param cs_name: name of central station
        :param profiles: name of profile (etp_name)
        '''
        self.AddMessage('Adding CS "%s" to group "%s" with profiles %s'%(cs_name, group_name, profiles))
        gr_id = self.GuiApi.Group.getGroupId(group_name)
        if not gr_id: return Status(False, 'Could not get group id')
        cs_id = self.GuiApi.CentralStations.getCSid(cs_name)
        if not cs_id: return Status(False, 'Could not get CS id')
        profiles = self.GuiApi.CentralStations.getProfileIds(profiles)
        if not profiles: return Status(False, 'Could not get profiles')
        result = self.GuiApi.Group.save_cs_links(groupId=gr_id, centralStationId=cs_id, profiles=profiles).status_code==200
        if result: return Status(True, 'CS link was added')
        return Status(False, 'CS link was not added')
    
    def AssertCSLinkWasAdded(self, group_name, cs_name, profiles):
        return self.AssertStatusWasSuccessfull(self.DoAddCSLink(group_name, cs_name, profiles))
        
    

    def AssertResponseCountLanguages(self, response): return self.DoCheckLanguages(self.AssertWasSuccesfull, response)
    def ExpectResponseCountLanguages(self, response): return self.DoCheckLanguages(self.ExpectWasSuccesfull, response)

    def DoCheckGroup(self, verificator, response):
        data = response.json()['data']['rows']
        groups = 0
        name = []
        for e in data:
            if u'utg_id' in e:
                groups +=1
                name.append(e[u'utg_name'])
        result = groups != 0
        message = 'Group(s) %s (%s)' %(groups, name)
        return verificator(result, message, message)

    def AssertResponseCountGroups(self, response): return self.DoCheckGroup(self.AssertWasSuccesfull, response)
    def ExpectResponseCountGroups(self, response): return self.DoCheckGroup(self.ExpectWasSuccesfull, response)

    def DoCheckPanelsInfo(self, response, serial, account, group):
        fields = ["unt_serial","unt_id","unt_account","unt_name","unt_model","uri_last_timestamp","uri_next_timestamp",
                  "uri_last_reviewed","uri_last_result","uri_repeat","_unt_module_bb","_unt_module_gprs","_utg_name",
                  "usr_name","uri_progress","uri_last_reviewed_timestamp","last","process"]
        data = response.json()['data']['rows']
        for panel in data:
            if panel['unt_serial']==serial:
                self.ExpectWasSuccesfull(panel['unt_serial']==serial, 'Serial is %s instead of %s'%(panel['unt_serial'], serial), 'Serial is %s'%panel['unt_serial'])
                self.ExpectWasSuccesfull(panel['unt_account']==account, 'Serial is %s instead of %s'%(panel['unt_account'],account), 'Serial is %s'%panel['unt_account'])
                self.ExpectWasSuccesfull(panel['unt_name']==serial, 'Serial is %s instead of %s'%(panel['unt_name'],serial), 'Serial is %s'%panel['unt_name'])
                self.ExpectWasSuccesfull(panel['_utg_name']==group, 'Serial is %s instead of %s'%(panel['_utg_name'],group), 'Serial is %s'%panel['_utg_name'])
                for field in fields:
                    if field in panel: self.ExpectWasSuccesfull(True, 'Field %s is not present' % field, 'Field %s is present' % field)

    def CheckFilters(self, response, filter, expected):
        data = response.json()['data']['rows']
        for panel in data:
            self.ExpectWasSuccesfull(panel[filter]==expected, '%s is %s instead of %s'%(filter, panel[filter], expected), '%s is %s'%(filter, panel[filter]))

    def CheckSuggestion(self, response, filter, expected):
        data = response.json()['data'][filter]['rows']
        for suggest in data:
            self.ExpectWasSuccesfull(suggest['suggest'] in expected, 'Suggestion %s is not correct'%suggest, 'Suggestion %s is correct'%suggest)

    def CountSuggesion(self, response, filter, start, count):
        if not start: start=0
        data = response.json()['data'][filter]
        if count: count = min([count, int(data['count'])])
        else: count = int(data['count'])
        expect_quantity = count - start
        actual_quantity = 0
        for suggest in data['rows']:
            actual_quantity+=1
        self.ExpectWasSuccesfull(actual_quantity==expect_quantity, '%s suggestion instead of %s'%(actual_quantity, expect_quantity), '%s suggestion'%actual_quantity)

    def DoCheckWhoAmI(self, verificator, response, user=None):
        if user is None: user=self.web.email
        data = response.json()['data']
        result = data['usr_email'] == user
        message = 'You are "%s" '%data['usr_email']
        return verificator(result, message, message)

    def AssertResponseWhoAmI(self, response, user=None): return self.DoCheckWhoAmI(self.AssertWasSuccesfull, response, user)
    def ExpectResponseWhoAmI(self, response, user=None): return self.DoCheckWhoAmI(self.ExpectWasSuccesfull, response, user)

    def DoCheckConfigData(self, verificator, response):
        data = response.json()['data']
        result = False
        if data['current'] and data['backup']: result = True
        message = 'Configuration have data'
        return verificator(result, message, message)

    def AssertResponseConfigData(self, response): return self.DoCheckConfigData(self.AssertWasSuccesfull, response)
    def ExpectResponseConfigData(self, response): return self.DoCheckConfigData(self.ExpectWasSuccesfull, response)

    def DoCheckConfig(self, verificator, response):
        data = response.json()['data']
        result = data['prs_type']
        message = 'Panel %s (id %s) - %s' %(data['_unt_serial'], data['unt_id'], data['prs_type'])
        return verificator(result, message, message)

    def AssertResponseConfig(self, response): return self.DoCheckConfig(self.AssertWasSuccesfull, response)
    def ExpectResponseConfig(self, response): return self.DoCheckConfig(self.ExpectWasSuccesfull, response)

    def DoCheckReportCount(self, verificator, response, count=None):
        data = response.json()['data']['rows']
        counter = 0
        for e in data:
            if u'ret_id' in e: counter+=1
        if count and count==counter: result = True
        else: result = counter != 0
        message = "Quantity is %s"%counter
        return verificator(result, message, message)

    def AssertResponseReportCount(self, response, count=None): return self.DoCheckReportCount(self.AssertWasSuccesfull, response, count)
    def ExpectResponseReportCount(self, response, count=None): return self.DoCheckReportCount(self.ExpectWasSuccesfull, response, count)
    def AssertResponseReportCountNone(self, response, count=None): return self.DoCheckReportCount(self.AssertNotSuccesfull, response, count)
    def ExpectResponseReportCountNone(self, response, count=None): return self.DoCheckReportCount(self.ExpectNotSuccesfull, response, count)

    def DoCheckRefreshData(self, verificator, response):
        data = response.json()['data']
        message = "panel in state '%s'"%data
        return verificator(data, message,message)

    def AssertResponseRefreshData(self, response): return self.DoCheckRefreshData(self.AssertWasSuccesfull, response)
    def ExpectResponseRefreshData(self, response): return self.DoCheckRefreshData(self.ExpectWasSuccesfull, response)

    def DoCheckRemoteInspectionResult(self, response, result=None):
        data = response.json()['data']['rows']
        if not result: result=int(response.json()['data']['count'])
        count = 0
        for inspection in data:
            self.AddMessage('Date and time: %s'%inspection['dt'])
            for i in inspection['result']:
                self.AddMessage('Result id %s, value - %s'%(str(i['id']), str(i['value'])))
            count +=1
        if not result: result = int(response.json()['data']['count'])
        self.ExpectWasSuccesfull(count==result, 'Not all results are present')

    def DoCheckRRICount(self, verificator, response, count, filter):
        data = response.json()['data'][filter]
        if data:
            result = int(data['count'])-count >=0
            return verificator(result, 'Quantity is not correct', 'Quantity is correct')

    def ExpectRRICount(self, response, count, filter): return self.DoCheckRRICount(self.ExpectWasSuccesfull, response, count, filter)

    def DoCheckProfiles(self, response):
        data = response.json()['data']['rows']
        count = response.json()['data']['count']
        profiles = 0
        for profile in data:
            profiles +=1
        result = profiles == count
        self.ExpectWasSuccesfull(result, '%s profiles' %profiles, '%s profiles' %profiles)

    def DoCheckCS(self, response, expected):
        """need to change in future"""
        data = response.json()['data']['rows']
        for cs in data:
            self.ExpectWasSuccesfull(cs['cls_name']==expected, 'Incorrect CS')

    def DoCheckUsersSuggestions(self, response):
        data = response.json()['data']['rows']
        exp_count = int(response.json()['data']['count'])
        count = 0
        for user in data:
            self.AddMessage('User %s is present'%user['usr_name'])
            count += 1
        self.ExpectWasSuccesfull(count==exp_count, 'Not all users in list', 'All users in list')

    def DoCheckUserActionLogSuggestions(self, response, suggestion):
        data = response.json()['data']['rows']
        exp_count = int(response.json()['data']['count'])
        count = 0
        for suggest in data:
            self.AddMessage('%s %s is present'%(suggestion, suggest['value']))
            count +=1
        self.ExpectWasSuccesfull(count==exp_count, 'Not all suggestions in list', 'All suggestions in list')

    def DoCheckUsersActionStatuses(self, response, filter, value):
        data = response.json()['data']['rows']
        for action in data:
            self.ExpectWasSuccesfull(action[filter]==value, 'Action %s in list (value is %s instead of %s)'%(action['id'], action[filter], value))

    def DoCheckRemarkResponse(self, response, value):
        remark = response.json()['data']['text']
        self.ExpectWasSuccesfull(remark==value, 'Incorrect content was add to remark', 'Content is correct')

    def DoCheckAllCSResponseData(self, response, filter, expected):
        data = response.json()['data']['rows']
        for i in data:
            if i[filter]==expected: self.AddSuccess('Filter is OK')
            else: self.AddFailure("Filter is not OK")
            
    def DoWaitProcessStatusReached(self, verificator, prs_id, exp_status, timeout=30.00, frequency=1.00):
        result = self.GuiApi.Processes.waitForStatus(prs_id, exp_status, timeout, frequency)
        success = 'Process with id "%s" reached status "%s"'%(prs_id, exp_status)
        failure = 'Process with id "%s" did not reach status "%s"'%(prs_id, exp_status)
        return verificator(result, failure, success)
    
    def ExpectProcessStatusWasReached(self, prs_id, exp_status, timeout=30.00, frequency=0.5): return self.DoWaitProcessStatusReached(self.ExpectWasSuccesfull, prs_id, exp_status, timeout=timeout, frequency=frequency)
    def AssertProcessStatusWasReached(self, prs_id, exp_status, timeout=30.00, frequency=0.5): return self.DoWaitProcessStatusReached(self.AssertWasSuccesfull, prs_id, exp_status, timeout=timeout, frequency=frequency)

    def ExpectProcessWasSucceeded(self, prs_id, timeout=30.00, frequency=1.0): return self.ExpectProcessStatusWasReached(prs_id, 'succeeded', timeout=timeout, frequency=frequency)
    def AssertProcessWasSucceeded(self, prs_id, timeout=30.00, frequency=1.0): return self.AssertProcessStatusWasReached(prs_id, 'succeeded', timeout=timeout, frequency=frequency)

    def ActivatePanel(self, unt_id):
        self.AddMessage('Activate panel')
        response = self.GuiApi.Unit.activate(unt_id=unt_id)
        self.CheckResponseCodeStatusSuccess(response)
        prs_id = response.json()['data']['prs_id']
        self.ExpectProcessStatusWasReached(prs_id, 'succeeded', 10)
        
    def waitDiscoveryStageAppearedInRedis(self, panel_serial, stage_name, timeout=10.00):
        for timer in StopWatch(timeout, 0.2):
            stages = self.SSH.getNeoDiscoveryStages(panel_serial)
            if stage_name in stages.keys():
                self.AddSuccess('Discovery stage "%s" is present in redis list tasks'%stage_name)
                return True
        self.AddFailure('Discovery stage "%s" is absent in redis list tasks' % stage_name)
        return False

    def ContentCheckerSuccess(self, response):
        try:
            if response['status']=='success': return True
            return False
        except: self.AddFailure('Response data is not expected')

    def ContentCheckerEntityNotFound(self, response):
        try:
            if response['status']=='error' and response['message']=='ENTITY_NOT_FOUND': return True
            return False
        except: self.AddFailure('Response data is not expected')

    def ContentCheckerBadRequestParam(self, response):
        try:
            if response['status']=='error' and response['message']=='BAD_REQUEST_PARAMS': return True
            return False
        except: self.AddFailure('Response data is not expected')

    def ContentCheckerDenied(self, response):
        try:
            if response['status']=='error' and response['message']=='DENIED': return True
            return False
        except: self.AddFailure('Response data is not expected')

    def ContentCheckerParamMissing(self, response):
        try:
            if response['status']=='error' and response['message']=='PARAMS_MISSING': return True
            return False
        except: self.AddFailure('Response data is not expected')

    def ContentCheckerEndpointNotFound(self, response):
        try:
            if response['status']=='error' and response['message']=='ENDPOINT_NOT_FOUND': return True
            return False
        except: self.AddFailure('Response data is not expected')

    def SetEncryption(self, serial: str, channel: str, encrypted: bool):
        unt_id = self.GuiApi.Units.getUnitId(serial)
        self.AddMessage('Set Encryption for {} to "{}"'.format(channel, encrypted))
        response = self.GuiApi.Diagnostic.setencryption(unt_id=unt_id, channel=channel, encrypted=encrypted)
        return response

    def AutoenrollmentForChanel(self, channel: str, value: bool):
        channels = {'bba': 'broadband', 'gprs': 'cellular'}
        self.AddMessage("%s Automatic enrollment for %s" % ('Enabled' if value else 'Disabled',
                                                            channels[channel].title()))
        response = self.GuiApi.MMI.changeOptions(option='%s_settings' % channels[channel],
                                                 isAutoEnrollmentEnabled=value)
        self.AssertResponseStatusCode(response, 200)

#*************************************************************************
#**** TEST :: CASE *******************************************************
#*************************************************************************
import os


class TestCase(JenkinsTestCase, ExtendedMethods):
    
    _randomizer = None
    

    def __init__( self, test, output, **kwargs) :
        #initialize basic class
        self.logfile = output
        super(TestCase,self).__init__(test)
       
        #create connection configuration
        self.connection = sequences.Namespace()
        self.connection . hostname = self.defaultconfig.connection['hostname']

        self.ssh = sequences.Namespace()
        self.ssh.user = self.defaultconfig.sshaccess['sshuser']
        self.ssh.password = self.defaultconfig.sshaccess['sshpwd']
        self.web = sequences.Namespace()
        self.web.email = self.defaultconfig.connection['username']
        self.web.password = self.defaultconfig.connection['password']
        self.email_client = sequences.Namespace()
        self.email_client.email = self.defaultconfig.Email['master_email']
        self.email_client.password = self.defaultconfig.Email['master_password']
        self.email_client.smtp = self.defaultconfig.Email['email_server']
        self.ftp = sequences.Namespace()
        self.ftp.hostname = 'ci-ftp.visonic'
        self.ftp.user = 'ci'
        self.ftp.password = 'visonic'
        self.ftp.folder = 'automation/reports'
        self.__ssh = None
        self.__gui_api = None
        
    @property
    def logFolder(self):
        return os.path.split(self.logfile)[0]

    @property
    def SSH(self):
        if not self.__ssh:
            self.__ssh = IpmpInitalSetup(self.connection.hostname, self.ssh.user, self.ssh.password, self.connection.logger)
        return self.__ssh

    @property
    def GuiApi(self):
        if not self.__gui_api:
            self.__gui_api = GuiApi(self.connection.hostname, logger=self.connection.logger)
        return self.__gui_api

    def Run(self, output, *args):
         #create instance of the logger
        logger = trackable.Logger(self.logfile,1)
        format = trackable.HtmlFormatter()
        target = trackable.FileHandler(self.logfile,'a','utf-8',True,0,0)
        target . setFormatter(format)
        logger . addHandler(target)
        self.connection.logger = logger

        # self.connection.logger.debug('Loaded tree from "%s" directory' %self.tree_dir)
        # self.connection.logger.debug('Language file at "%s" directory' % self.lang_dir)
        # self.connection.logger.debug('Using resources from "%s"' % self.managerURI)


        logfile = ''
        # try:
        # logfile = self.connection.logger.handlers[0].baseFilename
        filename = os.path.split(self.logfile)[1]
        foldername = os.path.split(os.path.split(self.logfile)[0])[1]
        logfile = os.path.join(foldername, filename)
        output.DoWrite('message', 'Automation log -->',
            extra={'makeup':'anchor', 'anchor':("%s" % logfile.replace('\\', '/'))}
            # extra={'makeup':'anchor', 'anchor':("%s" % logfile)}
        )
        # except:pass
        res =  super(TestCase, self).Run(output, *args)
        # forcely close log files
        for h in logger.handlers[:]:
            h.close()
        return res
    
    def CheckEmail(self, from_addr, subject):
        '''
        :param client:
        :param addr:
        :param subject:
        :return:
        '''
        attach = self.logFolder
        mailBox = IMAPClient(self.email_client.smtp, self.email_client.email, self.email_client.password, self.connection.logger)
        msg = mailBox.WaitForEmailFrom(from_addr, subject, attachment_folder=attach)
        if self.AssertWasSuccesfull(msg, 'Email was not received', 'Email was received'): return msg
        
    def ClearAllUnseenLetters(self):
        self.AddMessage('Remove all unseen letters from "%s" that was sent by "%s"'%(self.email_client.email, self.getEmailSender()))
        mailBox = IMAPClient(self.email_client.smtp, self.email_client.email, self.email_client.password,
                             self.connection.logger)
        mailBox.clearAllUnseenBySender(self.getEmailSender())

    def getCodeFromMail(self, msg):
        code = msg['text']
        match = re.search('Your access code: (\S+).*', code)
        if match is None: self.AddFailure('No code received in email')
        else:
            confirmcode = match.group(1)
            self.AddMessage('Received confirmation code %s' % confirmcode)
            return confirmcode
        
    def getEmailSender(self):
        return 'server%s' % self.connection.hostname.split('.')[-1]
        
    def SetupEmailSettings(self):
        self.AddMessage('Setup email settings on server')
        addr_name = 'server%s@visonic.com' % self.connection.hostname.split('.')[-1]
        from_name = self.getEmailSender()
        if self.SSH.checkSendMailSetupFrom(addr_name, from_name):
            # todo: reset session manager (need fix on server)
            self.SSH._sshopen()
            self.SSH._restart_services(['session_manager, presentation'])
            self.SSH.close()
            self.AddMessage('Email settings already match to needed')
            return
        self.SSH.setupSendmail(fromname=addr_name)
        self.SSH.setupSendMailFrom(addr_name, from_name)


    def RegisterPowerUser(self, client):
        '''
        :type client: RestAPIClient
        '''
        user = self.SSH.getPowerUserID(client.email)
        if not user:
            self.AddMessage('Register user %s' % client.email)
            response = client.register()
            self.AssertResponseCode(response, 204)
            register_msg = self.CheckEmail(self.getEmailSender(), 'Registration')
            code = self.getCodeFromMail(register_msg)
            self.AddMessage('Complete register user')
            response = client.complete_register(code)
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
            self.AddMessage('Set password for user')
            response = client.setPassword()
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
        else :
            self.AddSuccess('User "%s" has already registered' % client.email)

    def RegisterInstallerUser(self, client: RestInstaller):
        '''
        :type client: RestInstaller
        '''
        user = self.SSH.getInstallerUserID(client.email)
        if not user :
            self.AddMessage('Register user %s' % client.email)
            response = client.register()
            self.AssertTrue(response['status'], 'Response status False', 'Response status True')
            register_msg = self.CheckEmail(self.getEmailSender(), 'Registration')
            code = self.getCodeFromMail(register_msg)
            self.AddMessage('Complete register user')
            response = client.complete_register(code)
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
            self.AddMessage('Set password for user')
            response = client.setPassword()
            self.AssertResponseCode(response, 200)
            self.AddMessage('Response: %s' % response.json())
        else :
            self.AddSuccess('User "%s" has already registered' % client.email)
    
            
    def AuthenticatePowerUser(self, client):
        self.AddMessage('Authenticate user {} with password {}'.format(client.email, client.password))
        response = client.authenticate()
        self.AssertWasSuccesfull(response.status_code==200, 'Authenticate is not successful', 'Authenticate is successful')

    def LinkPanelToPowerUserIfNeeded(self, client, panel_web, alias='MyPanel', access_proof=None):
        '''
        :type client: RestAPIClient
        '''
        self.AddMessage('Check panel is added to user')
        panel_list = client.get(client.getCMD('linked_panels'))
        panel_list = client.getContent(panel_list)
        panel_list = [i['panel_serial'] for i in panel_list]
        self.AddMessage('List of linked panels: (%s)'%str().join(panel_list))
        if panel_web not in panel_list:
            self.AddMessage('Add panel "%s" to user "%s"' % (panel_web, client.email))
            cmd = client.getCMD('link_panel')
            self.AddMessage('Link panel to the user')
            params = dict(panel_serial=panel_web, master_user_code=client.panel.code, alias=alias)
            if access_proof is not None: params.update(dict(access_proof=access_proof))
            response = client.post(cmd, **params)
            self.AssertResponseCode(response, 204)
            client.session_token = None # reset session token if panel was not linked
        else:
            self.AddSuccess('Panel "%s" is already added to user "%s"'%(panel_web, client.email))

    def AssertResponseStatusCode(self, response, expected_code):
        return self.AssertResponseCode(response, expected_code)

    def CheckImageByUrl(self, url):
        url = 'http://%s%s' % (self.connection.hostname, url)
        self.AddMessage('Try to get image from URL "%s"' % url)
        response = self.GuiApi._get(url, verify=False)
        # response = requests.get(url, verify=False)
        self.AssertResponseStatusCode(response, 200)
        self.expect_content_pictures(response.content)

    def expect_content_pictures(self, content):
        try:
            Image.open(BytesIO(content))
            self.AddSuccess('Content was recognized as image')
        except IOError:
            self.AddFailure('Content was not recognized as image')

    def CheckVideoByUrl(self, url, expected_format):
        mime_types = dict(
            avi=['video/x-msvideo'],
            flv=['video/x-flv'],
            mp4=['video/mp4'],
            webm=['video/webm']
        )
        url = 'http://%s%s' % (self.connection.hostname, url)
        self.AddMessage('Try to get image from URL "%s"' % url)
        response = self.GuiApi._get(url, verify=False)
        # response = requests.get(url, verify=False)
        with open(os.path.join(os.path.dirname(self.logfile), 'file.%s' % expected_format), 'wb') as f:
            f.write(response.content)
        self.AssertResponseStatusCode(response, 200)
        mime = magic.Magic(mime=True)
        res = mime.from_buffer(response.content)
        self.AddMessage('MIME of got content is: %s' % res)
        result = res in mime_types[expected_format]
        failure = 'Content from URL "%s" was not recognized as video of "%s" format' % (url, expected_format)
        success = 'Content from URL "%s" was recognized as video of "%s" format' % (url, expected_format)
        self.ExpectTrue(result, failure, success)

    def check_image_link(self, response, pictures_count=10, video_count=1, video_request_type='preloaded'):
        _video_count = 0
        data = response.json()['data'][video_request_type]
        for preview in data:
            _video_count += 1
            _pictures_count = 0
            self.AddMessage('Check video is present by link')
            self.ExpectTrue(preview['video'], 'Video is missing!')
            for video in preview['video']:
                self.CheckVideoByUrl(preview['video'][video], video)
            self.AddMessage('Check frames are present by links')
            for image in preview['frames']:
                _pictures_count += 1
                self.CheckImageByUrl(image)
            self.ExpectTrue(_pictures_count == pictures_count,
                            'Video has {} pictures, expected {}'.format(_pictures_count, pictures_count))
            self.AddMessage('Check preview is present by link')
            self.CheckImageByUrl(preview['preview'])
        self.ExpectTrue(_video_count == video_count,
                        'Event has {} video, expected {}'.format(_video_count, video_count))

    def check_video_event(self, pictures_count, videos_count=1, video_id=None):
        video_id = video_id if video_id else self.GuiApi.Events.lastEventWithVideo(start=0, count=150)
        self.AssertTrue(video_id, 'Event with video was not found')
        self.AddMessage('Send "video" command with params: evt_id=%s' % video_id)
        response = self.GuiApi.Events.get_video(evt_id=video_id)
        self.CheckResponseCodeStatusSuccess(response)
        self.check_image_link(response, pictures_count, videos_count)

    def check_is_link(self, path_to_pictures: str, picture_number: int, expected_picture_number: int):
        picture_path = "{}/picture{}.jpg".format(path_to_pictures, picture_number)
        actual_picture_path = self.SSH.GetReadlinkInfo(picture_path).replace('\n', '')
        actual_picture = actual_picture_path.split('/')[-1]
        self.ExpectTrue(actual_picture == "picture{}.jpg".format(expected_picture_number),
                        "Frame {} != Frame {}".format(picture_number, expected_picture_number),
                        "Frame {} == Frame {}".format(picture_number, expected_picture_number))

    def enable_disable_system_online_offline_events(self, enable: bool):
        self.AddMessage('Try to {} generating system online/offline events'.
                        format('enable' if enable else 'disable'))
        response = self.GuiApi.MMI.set_supervision(doSendEmailOnOnlineOffline=False,
                                                   doSendSmsOnOnlineOffline=False,
                                                   doSendOneChannelPanelOnlineOffline=enable,
                                                   doSendTwoChannelPanelOnlineOffline=enable)
        self.CheckResponseCodeStatusSuccess(response)

    def enable_disable_ri_events(self, enable: bool):
        self.AddMessage('Try to {} generating "Succeed/Failed RI" events'.
                        format('enable' if enable else 'disable'))
        response = self.GuiApi.MMI.set_rri(doSendEmailOnSuccess=False,
                                           doGenerateResultEvent=enable)
        self.CheckResponseCodeStatusSuccess(response)

    def enable_disable_supervision_in_group(self, group_name, enable=True):
        comm = {"pmaster": {"bba": {"isEnabled": enable,
                                    "supervision": 5,
                                    "timeout": 60},
                            "gprs": {"isEnabled": enable,
                                     "supervision": 120,
                                     "timeout": 240}},
                "quazar": {"bba": {"isEnabled": enable, "supervision": 135, "timeout": 405},
                           "gprs": {"isEnabled": enable, "supervision": 135, "timeout": 405}},
                "quazar53": {"bba": {"isEnabled": enable, "supervision": 135, "timeout": 405},
                             "gprs": {"isEnabled": enable, "supervision": 135, "timeout": 405}}}
        res = self.GuiApi.Group.editGroup(name=group_name, communications=comm)
        self.CheckResponseCodeStatusSuccess(res)

    def change_supervision_period_in_group(self,
                                           group_name: str,
                                           communicator: str = None,
                                           bba_supervision: int = 135,
                                           gprs_supervision: int = 135):
        """
        If you want to reset param to default, set communicator to None
        """
        if communicator not in ['pmaster', 'quazar', 'quazar53', None]:
            self.AddFailure('Wrong communicator type!')
        comm = {"pmaster": {"bba": {"isEnabled": True,
                                    "supervision": 5,
                                    "timeout": 60},
                            "gprs": {"isEnabled": True,
                                     "supervision": 120,
                                     "timeout": 240}},
                "quazar": {"bba": {"isEnabled": True, "supervision": 135, "timeout": 405},
                           "gprs": {"isEnabled": True, "supervision": 135, "timeout": 405}},
                "quazar53": {"bba": {"isEnabled": True, "supervision": 135, "timeout": 405},
                             "gprs": {"isEnabled": True, "supervision": 135, "timeout": 405}}}
        if communicator:
            comm.update({communicator: {"bba":
                                            {"isEnabled": True,
                                             "supervision": bba_supervision,
                                             "timeout": bba_supervision + 10},
                                        "gprs":
                                            {"isEnabled": True,
                                             "supervision": gprs_supervision,
                                             "timeout": gprs_supervision + 10}
                                        }
                         })
        res = self.GuiApi.Group.editGroup(name=group_name, communications=comm)
        self.CheckResponseCodeStatusSuccess(res)
    #
    # def getRandomBatchId(self):
    #     lettersAndDigits = string.ascii_letters + string.digits
    #     return ''.join(random.choice(lettersAndDigits) for i in range(10))
    #
    # def startRRI(self, serial: str) -> int:
    #     self.AddSuccess('Start RRI')
    #     unt_id = self.GuiApi.Units.getUnitId(serial)
    #     response = self.GuiApi.RemoteInspection.initiate_inspection(unt_id=[unt_id], batch_id=self.getRandomBatchId())
    #     self.CheckResponseCodeStatusSuccess(response)
    #     return response.json()['data']['processes'][0]['prs_id']
