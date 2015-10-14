import json
from ckan.plugins.toolkit import missing, _
from ckanext.dara.schema import author_fields
from ckanext.dara.utils import list_dicter


def authors(key, data, errors, context):
    """
    transform author fields to JSON string and store it
    """
    
    # TODO make sure there's at least one author given AND each Author has
    # at least lastname
    
    # XXX Shouldn't the converter part be in converters, not in validators...?!
    
    if errors[key]:
        return
    
    value = data[key]
    fields = author_fields()
    
    if isinstance(value, basestring):
        return

    dl = list_dicter(value[:], [field.id for field in fields]) 

    # XXX plug in ORCID check here

    data[key] = json.dumps(dl)




#XXX just an example from some other code ######################################
def repeating_text_output(value):
    """
    Return stored json representation as a list, if
    value is already a list just pass it through.
    """
    
    import pdb; pdb.set_trace()
    if isinstance(value, list):
        return value
    if value is None:
        return []
    try:
        return json.loads(value)
    except ValueError:
        return [value]


def repeating_text(key, data, errors, context):
    """
    Accept repeating text input in the following forms
    and convert to a json list for storage:

    1. a list of strings, eg.

       ["Person One", "Person Two"]

    2. a single string value to allow single text fields to be
       migrated to repeating text

       "Person One"

    3. separate fields per language (for form submissions):

       fieldname-0 = "Person One"
       fieldname-1 = "Person Two"
    """
    # just in case there was an error before our validator,
    # bail out here because our errors won't be useful
    if errors[key]:
        return
    value = data[key]
    # 1. list of strings or 2. single string
    if value is not missing:
        if isinstance(value, basestring):
            value = [value]
        if not isinstance(value, list):
            errors[key].append(_('expecting list of strings'))
            return

        #import pdb; pdb.set_trace()
        out = []
        for element in value:
            if not isinstance(element, basestring):
                errors[key].append(_('invalid type for repeating text: %r')
                    % element)
                continue
            if isinstance(element, str):
                try:
                    element = element.decode('utf-8')
                except UnicodeDecodeError:
                    errors[key]. append(_('invalid encoding for "%s" value')
                        % lang)
                    continue

            #we sometimes get empty strings
            if element:
                out.append(element)


        if not errors[key]:
            data[key] = json.dumps(out)
        return

    # 3. separate fields
    found = {}
    prefix = key[-1] + '-'
    extras = data.get(key[:-1] + ('__extras',), {})

    for name, text in extras.iteritems():
        if not name.startswith(prefix):
            continue
        if not text:
            continue
        index = name.split('-', 1)[1]
        try:
            index = int(index)
        except ValueError:
            continue
        found[index] = text

    out = [found[i] for i in sorted(found)]
    data[key] = json.dumps(out)



