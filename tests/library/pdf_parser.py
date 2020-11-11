import io
import re
import time
from collections import OrderedDict

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage

from atl.logger import DummyLogger


class PDFReportParser(object):
    
    def __init__(self, path, logger=None):
        self.path = path
        self.logger = logger or DummyLogger()
        self._text = str()
        self.rows = list()
        self.extract_text()
        self.report = dict(
            serial = None,
            hostname = None,
            panelId = None,
            group = None,
            account = None,
            panel_type = None,
            firmware = None,
            last_connection = None,
            sim_number = None,
            supervision_bba = None,
            supervision_gsm = None,
            faults = None,
            processes = None,
            events = None,
            rri_results = None,
            generated = None,
        )
        self.rri_results = list()
        self.getters = dict(
            serial=         dict(pattern=r'Unit\:(.*)',          getter = lambda i: i),
            hostname=       dict(pattern=r'Hostname(.*)',        getter = lambda i: i),
            panelId=        dict(pattern=r'Panel ID(.*)',        getter = lambda i: i),
            group=          dict(pattern=r'Group Name(.*)',      getter = lambda i: i),
            account=        dict(pattern=r'Account Number(.*)',  getter = lambda i: i),
            panel_type=     dict(pattern=r'Panel Type(.*)',      getter = lambda i: i),
            firmware=       dict(pattern=r'Firmware Version(.*)',getter = lambda i: i),
            last_connection=dict(pattern=r'Last Connection(.*)', getter = lambda i: time.mktime(time.strptime(i,'%Y-%m-%d %H:%M:%S'))),
            sim_number=     dict(pattern=r'SIM Number(.*)',      getter = lambda i: i),
            supervision_bba=dict(pattern=r'Supervison BB(.*)',   getter = lambda i: int(i) if i else i),
            supervision_gsm=dict(pattern=r'Supervision GPRS(.*)',getter = lambda i: int(i) if i else i),
            generated =     dict(pattern=r'Page \d+ Generated on\:(.*)', getter = lambda i: i)
        )
        self.headers = OrderedDict((
            ('faults','Faults'),
            ('processes','Last 20 Processes'),
            ('events','Last 20 Events'),
            ('rri_results','RRI Results')
        ))
        self.remain_headers = None
        
    def extract_text(self):
        resource_manager = PDFResourceManager()
        fake_file_handle = io.StringIO()
        laparams = LAParams()
        laparams.char_margin = 1000
        laparams.word_margin = 0.01
        laparams.line_margin = 0.01
        converter = TextConverter(resource_manager, fake_file_handle, laparams=laparams)
        page_interpreter = PDFPageInterpreter(resource_manager, converter)
        page_interpreter.device.handle_undefined_char = lambda f, c : chr(c)
        with open(self.path, 'rb') as fh :
            for page in PDFPage.get_pages(fh, caching=True, check_extractable=True) :
                page_interpreter.process_page(page)
            self._text = fake_file_handle.getvalue()
            self.rows = self._text.split('\n')
        converter.close()
        fake_file_handle.close()
        
    def _parse_common(self):
        while self.rows:
            row = self.rows.pop(0)
            if not row.strip(): continue
            if row in self.headers.values():
                self.rows.insert(0, row)
                return
            for key, item in self.getters.items():
                pattern = item['pattern']
                getter = item['getter']
                match = re.match(pattern, row)
                if match is not None:
                    self.logger.debug('Matched row "%s" to key "%s"'%(row, key))
                    self.report[key] = getter(match.group(1).strip())
                    
    def _get_page_number_line(self, row):
        # if self.report['generated'] is not None: return False
        pattern = self.getters['generated']['pattern']
        getter = self.getters['generated']['getter']
        match = re.match(pattern, row)
        if match is None: return False
        self.report['generated'] = getter(match.group(1))
        return True
          
    def _get_container(self, header):
        start = False
        while self.rows:
            row = self.rows.pop(0)
            if not row: continue
            if self._get_page_number_line(row):
                match = re.match('.*\d{2}\:\d{2}\:\d{2}', self.rows[1])
                if match:
                    continue
                else:
                    return True
            if row in self.remain_headers.values():
                self.rows.insert(0, row)
                return
            if row == self.headers[header]:
                start = True
                self.report[header] = list()
                continue
            if not start:
                continue
            if re.match('\fRRI Report \d+ .*', row) and re.match('Reported Faults.*', self.rows[1]):
                self.rows.insert(0, row)
                return # got line with RRI
            match = re.match('.*\d{2}\:\d{2}\:\d{2}', row)
            if match is not None:
                self.report[header].append(''.join(c for c in row if ord(c) >= 32))
                
    def _get_ri_results(self):
        headers = ['Reported Faults', 'Total System Usage', 'Active Faults', 'Bypassed / In-test Zones',
                   'Frequently Used Zones', 'Check Clock', 'GPRS', 'Broadband', 'Soak Zones']
        result = dict()
        next_header = headers.pop(0)
        current_header = str()
        current_report = 0
        while self.rows:
            row = self.rows.pop(0)
            if not row: continue
            if self._get_page_number_line(row): continue
            if current_report<len(self.report['rri_results']) and \
                    '\f%s'%self.report['rri_results'][current_report]== row:
                try: self.rri_results.append(dict(name=self.report['rri_results'][current_report]))
                except IndexError: return
                continue
            if next_header in row:
                current_header = next_header
                if headers: next_header = headers.pop(0)
                self.rri_results[-1][current_header] = dict(result='', details=list())
                pattern = '.{0,1}%s (.*)'%current_header
                match = re.match(pattern, row)
                if match is not None:
                    self.rri_results[-1][current_header]['result'] = match.group(1)
                continue
            if current_header:
                self.rri_results[-1][current_header]['details'].append(row)
                
    
            
    def parseReport(self):
        self._parse_common()
        for header in self.headers.keys():
            self.remain_headers = self.headers.copy()
            self.remain_headers.pop(header)
            self._get_container(header)
        if self.report['rri_results']:
            self._get_ri_results()
        return self.report
            

if __name__ == '__main__':
    path = '/home/vitalyo/Downloads/failed tests/aaaa.pdf'
    import logging; logging.basicConfig(level='DEBUG')
    parser = PDFReportParser(path, logging)
    print(parser.parseReport())
    print('+'*100)
    for i in parser.rri_results:
        print(i)
    print('+'*100)
    print(parser.rows)
    
    # parser.getContainers()