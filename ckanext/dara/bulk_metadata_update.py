"""
    Script to update metadata in the JDA for fields that exist
"""
import ast
import sys
import json
import requests
import ckanapi
from pylons import config
from ckanext.dara.controller import darapi, auth
from ckanext.dara.controller import DaraController as dc

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# file handler
fh = logging.FileHandler('bulk_update.log')
fh.setLevel(logging.INFO)
# console handler
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

# set format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add handler
logger.addHandler(fh)
logger.addHandler(ch)


class BulkUpdater:
    def __init__(self, app, key, test=False):
        if test:
            self.obj = ckanapi.TestAppCKAN(app, apikey=key)
        else:
            self.obj = ckanapi.RemoteCKAN('http://www.journaldata.zbw.eu', apikey=key)
        self.lookup_base = u'http://www.zbw.eu/beta/econ-ws/suggest2?dataset=econ_corp&query={name}'


    def get_packages(self, limit=10, offset=0):
        return self.obj.action.package_list(limit=limit, offset=offset)


    def get_package(self, id):
        return self.obj.action.package_show(id=id)


    def get_resource(self, id):
        return self.obj.action.resource_show(id=id)


    def patch_package(self, id, update):
        return self.obj.action.package_patch(id=id, dara_authors=json.dumps(update, ensure_ascii=False))


    def patch_resource(self, id, update):
        return self.obj.action.resource_patch(id=id, dara_authors=json.dumps(update, ensure_ascii=False))


    def lookup(self, name):
        name = name.replace('-', ' ').replace('  ', ' ').replace('  ', ' ')
        url = self.lookup_base.format(name=name)
        try:
            r = requests.get(url).json()['results']
        except Exception as e:
            return False

        if len(r['bindings']) == 1:
            b_id = r['bindings'][0][u'concept'][u'value'].replace('http://d-nb.info/gnd/', '')
            return b_id

        for binding in r['bindings']:
            b_id=binding[u'concept'][u'value'].replace('http://d-nb.info/gnd/', '')
            prefLabel = binding[u'prefLabel'][u'value']
            prefName = binding[u'prefName'][u'value']

            if name == prefLabel or name == prefName:
                return b_id

        return False


    def update_affil_id(self, name):
        package = self.get_package(name)

        try:
            authors = package['dara_authors']
        except Exception as e:
            logger.warning('"{}" has no dara_authors'.format(name))
            return False, False

        updated = False
        updated_authors = []
        for author in json.loads(authors):
            aff = author['affil']
            if aff and aff != '':
                affID = self.lookup(aff)

                if affID != False and affID != '':
                    updated = True
                    author['affilID'] = affID
                updated_authors.append(author)

        return updated_authors, updated


    def update_affil_resource(self, id):
        package = self.get_resource(id)
        try:
            authors = package['dara_authors']
        except Exception as e:
            return False

        updated_authors = []

        authors = ast.literal_eval(authors)
        if len(authors) > 5:
            # chunk it up
            a = [authors[x:x+5] for x in xrange(0, len(authors), 5)]
            for author in a:
                aff = author[2]
                if aff and aff != '':
                    affID = self.lookup(aff)

                    if affID != False and affID != '':
                        author[4] = u'{}'.format(affID)
                        updated_authors = updated_authors + author
                    else:
                        updated_authors = updated_authors + author
        else:
            a = authors
            aff = a[2]
            if aff and aff != '':
                affID = self.lookup(aff)

                if affID != False and affID != '':

                    author[4] = u'{}'.format(affID)
            updated_authors = updated_authors + a

        return updated_authors


if __name__ == "__main__":
    logger.info('|=|=|=|Starting|=|=|=|')
    import os
    import configparser as cp
    path = os.path.dirname(os.path.abspath(__file__)) + '/../../test.ini'
    #path = '~/Python/src/ckanext-dara/ckanext/test.ini'
    config = cp.ConfigParser()
    #config.read_file(open(path))
    config.read(path)

    obj = BulkUpdater(None, key='d7aca98d-f0da-4dd4-b2bd-fc3e5d1e5682')
    auth = (config.get('app:main', 'ckanext.dara.user'),
            config.get('app:main', 'ckanext.dara.password'))

    packages = obj.get_packages(offset=100)
    count = 0
    updated_records = []
    errors = []
    for package in packages:
        details = obj.get_package(package)

        if int(details['dara_PublicationDate']) < 2019:
            # update metadata
            #if details['name'] == 'worker-personality-another-skill-bias-beyond-education-in-the-digital-age':
            new_authors, updated = obj.update_affil_id(details['name'])
            if updated and new_authors:
                try:
                    result=obj.patch_package(id=details['name'],update=new_authors)
                    updated_records.append(package)
                except Exception as e:
                    errors.append(('META:: {}: {}'.format(package, e)))


        # update DA|RA
        if details['dara_DOI'] and int(details['dara_PublicationDate']) < 2019:
            #print(details['dara_DOI'])
            #print(details['dara_PublicationDate'])
            count += 1
            #if details['name'] == 'worker-personality-another-skill-bias-beyond-education-in-the-digital-age':
            base = 'http://journaldata.zbw.eu/dataset/{id}/dara_xml'
            try:
                url = base.format(id=details['id'])
                new_xml = requests.get(url).content
                dara=darapi(auth, new_xml.decode('utf-8'), test=False, register=False)
            except Exception as e:
                errors.append(('DARA:: {}: {}'.format(package, e)))

    logger.info("{} files matched criteria".format(count))
    logger.info("\nFollowing files were updated:\n\t{}".format('\n\t'.join(updated_records)))
    logger.info("Encountered the following issues:\n\t{}".format('\n\t'.join(errors)))
    logger.info('|=|=|=|Finished|=|=|=|\n\n')




