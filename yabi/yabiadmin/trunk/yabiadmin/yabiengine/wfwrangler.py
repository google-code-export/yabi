import logging
logger = logging.getLogger('yabiengine')
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from yabiadmin.yabiengine.models import Task, Job, Workflow, Syslog, StageIn
from yabiadmin.yabmin.models import Backend, BackendCredential
from yabiadmin.yabiengine.YabiJobException import YabiJobException
from yabiadmin.yabiengine.urihelper import uriparse
from yabiadmin.yabiengine import backendhelper

def walk(workflow):

    for job in workflow.job_set.all().order_by("order"):
        logger.info('Walking job id: %s' % job.id)
        try:

            #check job status
            if not job.status_complete() and not job.status_ready():
                check_dependencies(job)
                prepare_tasks(job)
                prepare_job(job)
            else:
                logger.info('Job id: %s is %s' % (job.id, job.status))

            
        except YabiJobException,e:
            logger.info("Caught YabiJobException with message: " + e.message)
            continue


def check_dependencies(job):
    """Check each of the dependencies in the jobs command params.
    Start with a ready value of True and if any of the dependecies are not ready set ready to False.
    If dependencies are all met change job status to settings.STATUS['dependencies_ready']
    """
    logger.info('Check dependencies for jobid: %s...' % job.id)

    try:
        for param in eval(job.commandparams):

            if param.startswith("yabi://"):
                logger.info('Evaluating param: %s' % param)
                scheme, uriparts = uriparse(param)
                workflowid, jobid = uriparts.path.strip('/').split('/')
                param_job = Job.objects.get(workflow__id=workflowid, id=jobid)
                if param_job.status != settings.STATUS["complete"]:
                    raise YabiJobException("Job command parameter not complete. Job:%s Param:%s" % (job.id, param))

    except ObjectDoesNotExist, e:
        raise YabiJobException('Error with job param: %s' % e.message)


def prepare_tasks(job):
    logger.info('Preparing tasks for jobid: %s...' % job.id)

    input_files = []

    # get the backend for this job
    b = backendhelper.get_backend_from_uri(job.exec_backend)
    bc = BackendCredential.objects.get(backend=b, credential__user=job.workflow.user)

    paramlist = eval(job.commandparams)
    for param in paramlist:

        ##################################################
        # handle yabi:// uris
        ##################################################
        if param.startswith("yabi://"):
            logger.info('Processing uri %s' % param)

            # parse yabi uri
            # TODO we may want to look at server later, but just getting path for now
            scheme, uriparts = uriparse(param)
            workflowid, jobid = uriparts.path.strip('/').split('/')
            param_job = Job.objects.get(workflow__id=workflowid, id=jobid)
            
            # get stage out directory of job
            stageout = param_job.stageout

            paramlist.append(stageout)


        ##################################################
        # handle file:// uris that are directories
        ##################################################

        # uris ending with a / on the end of the path are directories
        elif param.startswith("file://") and param.endswith("/"):
            logger.info('Processing uri %s' % param)

            # get_file_list will return a list of file tuples
            for f in backendhelper.get_file_list(param):
                create_task(job, param, f[0], b, bc)


        ##################################################
        # handle file:// uris
        ##################################################
        elif param.startswith("file://"):
            logger.info('Processing uri %s' % param)            
            rest, filename = param.rsplit("/",1)
            create_task(job, rest + "/", filename, b, bc)
            input_files.append(param)


        ##################################################
        # handle unknown types
        ##################################################
        else:
            logger.info('****************************************')
            logger.info('Unhandled type: ' + param)
            logger.info('****************************************')



def prepare_job(job):
    logger.info('Setting job id %s to ready' % job.id)                
    job.status = settings.STATUS["ready"]
    job.save()


def create_task(job, param, file, backend, backendcredential):

    param_scheme, param_uriparts = uriparse(param)
    backend_scheme, backend_uriparts = uriparse(backendcredential.homedir)
    
    taskcommand = job.command.replace("%", "%s%s%s" % (backend.path, backend_uriparts.path,file))
    logger.info('Creating task for job id: %s using command: %s' % (job.id, taskcommand))
    t = Task(job=job, command=taskcommand, status="ready")
    t.save()


    s = StageIn(task=t,
                src_backend=param_scheme,
                src_path="%s%s" % (param_uriparts.path, file),
                dst_backend=job.fs_backend,
                dst_path="%s%s" % (backend_uriparts.path, file),
                order=0)
    s.save()


