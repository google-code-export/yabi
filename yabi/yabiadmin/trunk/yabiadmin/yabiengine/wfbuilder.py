from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from yabiadmin.yabiengine.models import Task, Job, Workflow, Syslog, StageIn
from yabiadmin.yabmin.models import Backend, BackendCredential, Tool, User
from yabiadmin.yabiengine.YabiJobException import YabiJobException
from yabiadmin.yabiengine.urihelper import uri_get_pseudopath
from yabiadmin.yabiengine import backendhelper
from django.utils import simplejson as json
from yabiengine import wfwrangler
import datetime
import os

import logging
import yabilogging
logger = logging.getLogger('yabiengine')


job_cache = {}

def build(username, workflow_json):
    logger.debug('')
    
    workflow_dict = json.loads(workflow_json)
    job_cache = {}

    try:

        user = User.objects.get(name=username)
        workflow = Workflow(name=slugify(workflow_dict["name"]), json=workflow_json, user=user)
        workflow.save()

        for i,job_dict in enumerate(workflow_dict["jobs"]):
            job = addJob(workflow, job_dict, i)

        # start processing
        logger.debug('-----Starting workflow id %d -----' % workflow.id)
        wfwrangler.walk(workflow)

    except ObjectDoesNotExist, e:
        logger.critical(e)
        raise
    except KeyError, e:
        logger.critical(e)
        raise
    except Exception, e:
        logger.critical(e)
        raise



def addJob(workflow, job_dict, order):
    logger.debug('')

    tool = Tool.objects.get(name=job_dict["toolName"])

    job = Job(workflow=workflow, order=order, start_time=datetime.datetime.now())
    job.save()

    # cache job for later reference
    job_id = job_dict["jobId"] # the id that is used in the json
    job_cache[job_id] = job

    # process the parameterList to get a useful dict
    param_dict = {}
    for toolparam in job_dict["parameterList"]["parameter"]:
        param_dict[toolparam["switchName"]] = get_param_value(workflow, toolparam)

    # now build up the command
    command = []
    commandparams = []

    command.append(tool.path)

    for tp in tool.toolparameter_set.order_by('rank').all():

        # check the tool switch against the incoming params
        if tp.switch not in param_dict:
            continue

        # if the switch is the batch on param switch put it in commandparams and add placeholder in command
        if tp == tool.batch_on_param:
            commandparams.append(param_dict[tp.switch])
            param_dict[tp.switch] = '%' # use place holder now in command

        # run through all the possible switch uses
        switchuse = tp.switch_use.value

        if switchuse == 'switchOnly':
            command.append(tp.switch)

        elif switchuse == 'valueOnly':
            command.append(param_dict[tp.switch])

        elif switchuse == 'both':
            command.append("%s %s" % (tp.switch, param_dict[tp.switch]))

        elif switchuse == 'combined':
            command.append("%s%s" % (tp.switch, param_dict[tp.switch]))

        elif switchuse == 'pair':
            pass # TODO figure out what to do with this one

        elif switchuse == 'none':
            pass


    # add other attributes
    job.command = ' '.join(command)
    job.commandparams = repr(commandparams) # save string repr of list


    # set status to complete if null backend
    if tool.backend.name == 'nullbackend':
        job.status = settings.STATUS['complete']
    else:
        job.status = settings.STATUS['pending']

    # add a list of input file extensions as string, we will reconstitute this for use in the wfwrangler
    job.input_filetype_extensions = str(tool.input_filetype_extensions())


    ## TODO raise error when no credential for user
    logger.debug('%s - %s' % (workflow.user, tool.fs_backend))
    exec_backendcredential = BackendCredential.objects.get(credential__user=workflow.user, backend=tool.backend)
    fs_backendcredential = BackendCredential.objects.get(credential__user=workflow.user, backend=tool.fs_backend)

    #TODO hardcoded
    if tool.backend.name == 'nullbackend':
        job.stageout = None
    else:
        job.stageout = "%s%s%d/%d/" % (tool.fs_backend.uri, fs_backendcredential.homedir, workflow.id, job.id)


    job.exec_backend = exec_backendcredential.homedir_uri
    job.fs_backend = fs_backendcredential.homedir_uri

    job.cpus = tool.cpus
    job.walltime = tool.walltime
    job.save()


def get_param_value(workflow, tp):
    logger.debug('')

    logger.debug("====================: %s" % tp)
    
    value = ''
    if type(tp["value"]) == list:
        for item in tp["value"]:

            if type(item) == dict:

                # handle links to previous nodes
                if 'type' in item and 'jobId' in item:
                    # TODO - adding localhost.localdomain to uri at the moment, should this be pulled in from somewhere

                    previous_job = job_cache[item['jobId']]

                    if previous_job.stageout == None:
                        value = eval(previous_job.commandparams)[0] # TODO this is a bit of a hack
                    else:
                        value = u"yabi://localhost.localdomain/%d/%d/" % (workflow.id, job_cache[item['jobId']].id)

                # handle links to previous file selects
                elif 'type' in item and 'filename' in item and 'root' in item:
                    path = ''
                    if item['path']:
                        path = os.path.join(*item['path'])
                        if not path.endswith(os.sep):
                            path = path + os.sep
                    value = '%s%s%s' % (item['root'], path, item['filename'])

                
            elif type(item) == str or type(item) == unicode:
                value += item

    logger.debug(value)
    return value



def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    TODO this function is from djangos defaultfilters.py which is not in mango
    we should work on getting these back into mango and take advantage of all
    of djangos safe string stuff
    """
    logger.debug('')

    import unicodedata
    import re
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)
