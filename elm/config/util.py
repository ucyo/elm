
from pkg_resources import resource_stream, Requirement
import json
import os
import traceback
import yaml


EXAMPLE_CALLABLE = 'elm.preproc:resampling'

def read_from_egg(tfile, file_type='yaml'):
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), tfile)
    if not os.path.exists(template_path):
        path_in_egg = os.path.join("elm", tfile)
        buf = resource_stream(Requirement.parse("elm"), path_in_egg)
        _bytes = buf.read()
        contents = str(_bytes)
    else:
        with open(template_path, 'r') as f:
            contents = f.read()
    if file_type == 'yaml':
        return yaml.load(contents)
    elif file_type == 'json':
        return json.loads(contents)
    else:
        return contents


class ElmConfigError(ValueError):
    pass


def import_callable(func_or_not, required=True, context=''):
    if callable(func_or_not):
        return func_or_not
    context = context + ' -  e' if context else 'E'
    if func_or_not and (not isinstance(func_or_not, str) or func_or_not.count(':') != 1):
        raise ElmConfigError('{}xpected {} to be an module:callable '
                               'if given, e.g. {}'.format(context, repr(func_or_not), EXAMPLE_CALLABLE))
    if not func_or_not and not required:
        return
    elif not func_or_not:
        raise ElmConfigError('{}xpected a callable, '
                               'e.g. {} but got {}'.format(context, EXAMPLE_CALLABLE, repr(func_or_not)))
    module, func = func_or_not.split(':')
    try:
        mod = __import__(module, globals(), locals(), [func], 0)
    except Exception as e:
        tb = traceback.format_exc()
        raise ElmConfigError('{}xpected module {} to be '
                               'imported but failed:\n{}'.format(context,func_or_not, tb))
    func = getattr(mod, func, None)
    if not callable(func):
        raise ElmConfigError('{}xpected {} to be callable - '
                               'it was imported but it is not '
                               'callable'.format(context, func_or_not))
    return func