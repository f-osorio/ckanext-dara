# Hendrik Bunke
# ZBW - Leibniz Information Centre for Economics

from ckan.controllers.package import PackageController
import ckan.plugins.toolkit as tk
from ckan.common import c, response
from ckan import model
import ckan.lib.helpers as h
from StringIO import StringIO
from lxml import etree
from datetime import datetime
from ckanext.dara.dara_schema.v3_1 import schema
from pylons import config
from ckanext.dara.ftools import memoize
import requests
from toolz.dicttoolz import keyfilter, get_in


class DaraError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class DaraController(PackageController):
    """
    displays and validates dara XML for the dataset or resource, and registers
    it at da|ra.
    """

    def _context(self):
        return {'model': model, 'session': model.Session,
                'user': c.user or c.author, 'for_view': True,
                'auth_user_obj': c.userobj}
    
    def _check_access(self, id):
        context = self._context()
        try:
            tk.check_access('package_update', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(401, 'Unauthorized to manage DOI.')
    
    def register(self, id, template):
        """
        register at da|ra
        """
        self._check_access(id)
        context = self._context()

        def store():
            if params()['register'] or params()['test_register']:
                # XXX in case of update we might not need to store the DOI
                c.pkg_dict['dara_DOI'] = c.pkg_dict['dara_DOI_Proposal']
            tk.get_action('package_update')(context, c.pkg_dict)
    
        def response():
            a = {201: ('dara_registered', 'Dataset registered'),
                 200: ('dara_updated', 'Dataset updated')}
            if dara in a.iterkeys():
                date = '{:%Y-%m-%d-%H:%M:%S}'.format(datetime.now())
                k = get_in([dara, 0], a)
                c.pkg_dict[k] = date
                store()
                h.flash_success(get_in([dara, 1], a))
            else:
                h.flash_error("ERROR! Sorry, dataset has not been registered or\
                          updated. Please contact your friendly sysadmin. ({})\
                          ".format(dara))
            tk.redirect_to('dara_doi', id=id)

        def register_resources():
            def reg(resource):
                resource_id = resource['id']
                c.resource = tk.get_action('resource_show')(context, {'id': resource_id})
                xml = self.xml(id, 'package/resource.xml')
                dara = darapi(auth(), xml, test=params()['test'],
                        register=params()['register'])
                if dara in (200, 201):
                    doi = u'{}.{}'.format(c.pkg_dict['dara_DOI_Proposal'],
                            resource['dara_doiid'])
                    c.resource['dara_DOI'] = doi
                    tk.get_action('resource_update')(context, c.resource)
                else:
                    h.flash_error("ERROR! Resource {} could not be registered ({}).\
                            Dataset has not been registered".format(resource_id, dara))
                    tk.redirect_to('dara_doi', id=id)
        
            c.pkg_dict = tk.get_action('package_show')(context, {'id': id})
            resources = filter(lambda res: res['id'] in tk.request.params,
                    c.pkg_dict['resources'])
            map(lambda resource: reg(resource), resources)

        # first register resources
        register_resources()
                
        # register package
        c.pkg_dict = tk.get_action('package_show')(context, {'id': id})
        dara = darapi(auth(), self.xml(id, template),
                    test=params()['test'], register=params()['register'])
        response()

    def xml(self, id, template):
        """
        returning valid dara XML
        """
        response.headers['Content-Type'] = "text/xml; charset=utf-8"
        xml_string = tk.render(template)
        
        # validate
        xmlschema_doc = etree.parse(StringIO(schema))
        xmlschema = etree.XMLSchema(xmlschema_doc)
        doc = etree.parse(StringIO(xml_string))
        xmlschema.assertValid(doc)

        return xml_string
    
    def doi(self, id, template):
        """
        DOI manager page
        """
        self._check_access(id)
        context = self._context()
        c.pkg_dict = tk.get_action('package_show')(context, {'id': id})
        c.pkg = context['package']
        return tk.render(template)


@memoize
def params():
    """
    test for parameters. For testserver DOI registration is not possible,
    so we fake it (test_register).
    defaults: register at 'real' server and get a DOI
    """
    ptest = lambda p: p in tk.request.params

    # XXX change this for production
    # test = ptest('testserver')
    test = True
    test_register = False
    register = ptest('DOI')

    if test and register:
        register = False
        test_register = True

    return {'test': test, 'register': register,
            'test_register': test_register}


@memoize
def auth():
    def gc(kw):
        auths = map(lambda t: config.get(t, False), kw)
        if False in auths:  # if False...? hm...
            raise DaraError("User and/or password ({}, {}) not \
                   set in CKAN config".format(kw[0], kw[1]))
        return tuple(auths)  # requests needs tuple

    if params()['test']:
        return gc(['ckanext.dara.demo.user', 'ckanext.dara.demo.password'])
    return gc(['ckanext.dara.user', 'ckanext.dara.password'])
    

def darapi(auth, xml, test=False, register=False):
    """
    talking with da|ra API. See da|ra reference:
    http://www.da-ra.de/fileadmin/media/da-ra.de/PDFs/dara_API_reference_v1.pdf

    :param auth: tuple with username and password for the account at da|ra for
                 the account at da|ra
    :param xml: the XML string to post to da|ra, *without* the <?xml ... ?>
                instruction. XML must validate against the dara XSD-Schema
    :param test: if True connects to dara production server, otherwise it uses
                the test-server (default: False)
    :param register: register a DOI. Note that the test server cannot register
                    DOI. If you try it will return an additional message
                    (default: False)

    da|ra response http codes:
        201 Created operation successful, returned if a new dataset created
        200 OK operation successful, returned if an existing dataset updated
        400 Bad Request - request body must be valid xml
        401 Unauthorized - no or wrong login
        500 Internal Server Error - server internal error, try later and if
            problem persists please contact da|ra

    '500' usually means that there's an error in your request. It unfortunately
    also returns a huge chunk of html output. However, it can be used for
    debugging.
    """
    
    url = 'http://www.da-ra.de/dara/study/importXML'
    if test:
        url = 'http://dara-test.gesis.org:8084/dara/study/importXML'

    # socket does not take unicode, so we need to encode our unicode object
    # see http://stackoverflow.com/questions/9752521/sending-utf-8-with-sockets
    # XXX do we always get unicode object???
    xml_encoded = xml.encode('utf-8')
    
    params = keyfilter(lambda x: register, {'registration': 'true'})
    headers = {'content-type': 'application/xml;charset=UTF-8'}
    req = requests.post(url, auth=auth, headers=headers, data=xml_encoded,
            params=params)
    return req.status_code


