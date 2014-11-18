#Hendrik Bunke
#ZBW - Leibniz Information Centre for Economics


from ckan.controllers.package import PackageController
import ckan.plugins.toolkit as tk
from ckan.common import c, request, response
from ckan import model
import ckan.lib.helpers as h
from StringIO import StringIO
from ckanext.dara.dara_schema_3 import schema
from lxml import etree
from darapi import DaraClient
from datetime import datetime
from hashids import Hashids
import random


NotAuthorized = tk.NotAuthorized



class DaraController(PackageController):
    """
    displays and validates dara XML for the dataset or resource, and registers
    it at da|ra
    """
    

    def __init__(self):
        self.schema = schema
        
        
    def xml(self, id):
        """
        returning dara xml
        """
        
        response.headers['Content-Type'] = "text/xml; charset=utf-8"
        template = "package/read.xml"
        xml_string = tk.render(template)

        #validate before show. Errors are caught by lxml
        #XXX perhaps it makes more sense to validate later in the process (before
        #submitting to dara, for example)
        self._validate(xml_string)

        return xml_string
    
    
    def register(self, id):
        """
        register at da|ra
        """
        #XXX darapi is too small, should it be integrated here?
        
        ## using tk.c as context does not work here
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id}

        try:
            tk.check_access('package_update', context, data_dict)
        except NotAuthorized:
            tk.abort(401, 'Unauthorized to manage DOI.')

        
        xml = self.xml(id)
        c.pkg_dict = tk.get_action('package_show')(context, data_dict)
                
        #TODO: test for combo testserver=true and DOI=true, which is not
        #possible. Should be helper in template
        test = True
        register = False
        req = tk.request
        p = req.params
        if not 'testserver' in p:
            test = False
        if 'DOI' in p:
            register = True

        dara = DaraClient('demo', 'testdemo', xml, test=test, register=register)
        dara = dara.calldara()
    
        
        date = datetime.now()
        datestring = date.strftime("%Y-%m-%d-%H:%M:%S")

        if dara == 201:
            c.pkg_dict['dara_registered'] = datestring
            tk.get_action('package_update')(context, c.pkg_dict)
            h.flash_success("Dataset successfully registered.")
        elif dara == 200:
            c.pkg_dict['dara_updated'] = datestring
            tk.get_action('package_update')(context, c.pkg_dict)
            h.flash_success("Dataset successfully updated.")
        else:
            h.flash_error("ERROR! Sorry, dataset has not been registered or "
                    "updated. Please consult the logs. (%s) " %dara)

        tk.redirect_to('dara_doi', id=id)

        #return dara
        
    
    def doi(self, id):
        """
        DOI manager page
        """

        #XXX docs say that context is inherent. However, we do get wrong
        #breadcrumbs when not getting context here explicitly. Getting it with
        #toolkit.c throws error 'str is not callable'
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id}

        # Package needs to have a organization group in the call to
        # check_access and also to save it
        
        try:
            tk.check_access('package_update', context, data_dict)
        except NotAuthorized:
            tk.abort(401, 'Unauthorized to manage DOI.')


        c.pkg_dict = tk.get_action('package_show')(context, data_dict)
        c.pkg = context['package']
            
        template = "package/dara.html"
        page = tk.render(template)

        return page
    
    
    def _create_doi(self, pkg_dict):
        """
        this should go in a function directly after package is created. 
        DOI would than be stored in pkg_dict and not created here. That way we 
        could use random ints. For now it only takes the pkg creation date and
        creates a unique hash of it. If there are than one uploads in one second
        and for the same journal/organization we'd have a collision. This case
        might be rare ;-)
        """
        #XXX to be removed! deprecated. DOIs should be in pkg_dict

        prefix = u"10.2345" #XXX fake! change this. could be config
        
        org = pkg_dict['organization']
        journal = org['name']
        hashids = Hashids()
        created = pkg_dict['metadata_created'] #date string
        dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S.%f") #object
        datestring = dt.strftime("%Y%m%d%H%M%S")
        
        ###XXX only use random int when doi is created and stored directly after
        #package creation
        #numrange = range(0,100) #twodigit
        #rd_num = random.choice(numrange)
        #date  = datestring + str(rd_num)
        
        date = int(datestring)
        num = hashids.encrypt(date)

        doi = prefix + '/' + journal + '.' + num

        return doi
        
    
    def _validate(self, xmlstring):
        """
        validate against dara schema. errors are thrown by lxml
        """
        
        xml = StringIO(xmlstring)
        xsd = StringIO(self.schema)
        xmlschema_doc = etree.parse(xsd)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        doc = etree.parse(xml)
        xmlschema.assertValid(doc)
    
    #for old datasets or such where doi proposals are not saved for whatever
    #reason
    def doi_proposal(self, id):
        
        try:
            tk.check_access('package_create', context)
        except NotAuthorized:
            tk.abort(401, 'Unauthorized to manage DOI')

        pkg = tk.get_action('package_show')(None, {'id': id})
        key = 'dara_DOI_Proposal'
        if key in pkg and pkg[key]:
            return "Has already DOI: %s" %pkg[key]
        doi = self._create_doi(pkg)
        tk.get_action('package_update')(None, {'id': id, 'dara_DOI_Proposal': doi})
        return 'Done!'
        


