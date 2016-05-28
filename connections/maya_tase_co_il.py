#!/usr/bin/python
import requesocks as requests
from scrapy.selector import Selector
import os

class NoSuchElementException(Exception):
    pass

class company_details_scraper:
    def __init__(self, url):
        self.url = url
        self.jobs = []

        self.session = requests.Session()
        proxy = os.environ.get('PROXY')
        if proxy is not None:
            self.session.proxies = {'http': 'socks5://'+proxy}

        self.request('get')
        self.extract_company_details()
        self.extract_nose_misra()

    def request( self, *p, **d ):
        if self.session is None:
            self.session = requests.Session()

            proxy = os.environ.get('PROXY')
            if proxy is not None:
                self.session.proxies = {'http': 'socks5://'+proxy}

        d.setdefault( 'timeout', 180 )
        d.setdefault( 'url', self.url )


        i = 0
        while True:
            try:
                self.response = self.session.request( *p, **d )
                break
            except Exception,e:
                i += 1
                handle_expected_exceptions( i, "search_web_page.request: Got %s, retrying (%d)" % (repr(e),i), max_retrys=3 )
                


        self.sel = Selector(text=self.response.content.decode('windows-1255', errors='replace'))

    def extract_company_details(self):
        # /html/body/form/center/table[3]/tbody/tr/td[2]/table/tbody/tr/td[2]/font
        company_name = self.sel.xpath('/html/body/form/center/table[3]/tr/td[2]/table/tr/td[2]/font/text()')
        if not company_name:
            raise NoSuchElementException()

        # /html/body/form/center/table[5]/tbody/tr[4]/td[3]
        company_id = self.sel.xpath('/html/body/form/center/table[5]/tr[4]/td[3]/text()')
        if not company_id:
            raise NoSuchElementException()

        self.company_name = company_name[0].extract()
        self.company_id = company_id[0].extract()
            

    def extract_nose_misra(self):
        # /html/body/form/center/table[12]/tbody/tr[2]/td[8]/b # name
        # /html/body/form/center/table[12]/tbody/tr[2]/td[7]/b # title
        tables = self.sel.xpath('/html/body/form/center/table')
        for table_index, title_table in enumerate(tables):
            table_title = title_table.xpath('tr/td[3]/font/a/@name')
            if not table_title:
                continue

            if table_title[0].extract() != 'NoseMisra':
                continue
            
            data_table = tables[table_index+2]
            for row in data_table.xpath('tr')[1:]:
                name = row.xpath('td[8]')
                if not name:
                    continue
                if name[0].xpath('b'):
                    name = name[0].xpath('b')

                title = row.xpath('td[7]')
                if not title:
                    continue
                if title[0].xpath('b'):
                    title = title[0].xpath('b')

                name_str = name[0].xpath('text()')[0].extract().strip()
                if not name_str:
                    continue

                self.jobs.append({
                    'name':name_str,
                    'title':title[0].xpath('text()')[0].extract()})

class company_numbers_scraper:
    def __init__(self, save_path):
        self.save_path = save_path
        self.access_script = os.path.join(os.path.split(__file__)[0], 'cmbHavGetV.js')
        self.url = 'http://maya.tase.co.il/bursa/jsScript/cmbHav.js'

        self.session = requests.Session()
        proxy = os.environ.get('PROXY')
        if proxy is not None:
            self.session.proxies = {'http': 'socks5://'+proxy}
        self.request('get')
        self.extract_company_indexes()

    def request( self, *p, **d ):
        if self.session is None:
            self.session = requests.Session()

            proxy = os.environ.get('PROXY')
            if proxy is not None:
                self.session.proxies = {'http': 'socks5://'+proxy}

        d.setdefault( 'timeout', 180 )
        d.setdefault( 'url', self.url )


        i = 0
        while True:
            try:
                self.response = self.session.request( *p, **d )
                break
            except Exception,e:
                i += 1
                handle_expected_exceptions( i, "search_web_page.request: Got %s, retrying (%d)" % (repr(e),i), max_retrys=3 )
                
        f = open(self.save_path,'w')
        f.write(self.response.content)
        f.close()

    def get_numbers(self, index):
        cmd = 'nodejs %s %s %d' % (self.access_script, self.save_path, index)
        str_data = os.popen(cmd, 'r').read()
        return [int(x) for x in str_data.split(',')]

    def extract_company_indexes(self):
        indexes = []
        for company_group in self.get_numbers(1):
            indexes.extend(self.get_numbers(company_group))
        self.indexes = set(indexes)
        
    def __iter__(self):
        return self.indexes.__iter__()

def test():
    import csv
    w = csv.writer(open('1.csv', 'w'))
    for url in ['http://maya.tase.co.il/bursa/CompanyDetails.asp?CompanyCd=343',
                'http://maya.tase.co.il/bursa/CompanyDetails.asp?CompanyCd=612',
                'http://maya.tase.co.il/bursa/CompanyDetails.asp?CompanyCd=1610&company_group=3000']:

        company = company_details_scraper(url)
        #print company.company_name, company.company_id, len(company.jobs)
        w.writerow([company.company_name.encode('cp1255'), 
                    company.company_id.encode('cp1255'), 
                    len(company.jobs)])


def extract_all(company_numbers_filename, csv_filename=None, json_filename=None):
    import csv
    import json

    print "extracting company ids..."
    company_numbers = company_numbers_scraper(company_numbers_filename)

    headings = ['name1', 'id1', 'name2', 'id2', 'connection_type', 'source']

    if csv_filename:
        csv_file = csv.writer(open(csv_filename, 'w'))
        csv_file.writerow(headings)
    if json_filename:
        json_file = open(json_filename,'w')

    for n in company_numbers:
        url = 'http://maya.tase.co.il/bursa/CompanyDetails.asp?CompanyCd=%d' % (n)
        company = company_details_scraper(url)
        print company.company_name, company.company_id, len(company.jobs)

        for job in company.jobs:
            row = {'name1':company.company_name, 'id1':company.company_id,
                   'name2':job['name'], 'id2':'',
                   'connection_type':job['title'],
                   'source':url}
                   
            if csv_filename:
                csv_file.writerow([row[x].encode('cp1255') for x in headings])
            if json_filename:
                json_file.write(json.dumps(row)+'\n')

if __name__ == "__main__":

    from optparse import OptionParser

    parser = OptionParser( usage='usage: %prog [options]' )
    parser.add_option("--temp-filename", dest="temp_filename", action='store', help='a temp filename path', default=None)
    parser.add_option("--csv-filename",  dest="csv_filename", action='store', help='csv output filename', default=None)
    parser.add_option("--json-filename", dest="json_filename", action='store', help='json output filename', default=None)

    (options, args) = parser.parse_args()

    if not options.temp_filename:
        parser.error( 'must provide an temp filename' )

    if not options.csv_filename and not options.json_filename:
        parser.error( 'must provide either a json filename or a csv filename' )

    extract_all(company_numbers_filename=options.temp_filename, csv_filename=options.csv_filename, json_filename=options.json_filename)

