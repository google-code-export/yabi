import logging
logger = logging.getLogger(__name__)
import sys
logger.debug("sys path = %s" % sys.path)

from yabiadmin.backend.sshbackend import SSHBackend
from yabiadmin.yabiengine.urihelper import uriparse
from yabiadmin.backend.pbsproparsers import PBSProParser, PBSProQSubResult, PBSProQStatResult
from yabiadmin.backend.exceptions import RetryException




class SSHPBSProExecBackend(SSHBackend):
    QSUB_TEMPLATE = "\n".join(["#!/bin/sh",
                    'script_temp_file_name="{0}"',
                    "cat<<EOS>$script_temp_file_name",
                    "{1}",
                    "EOS",
                    "qsub $script_temp_file_name"])

    QSTAT_TEMPLATE = "\n".join(["#!/bin/sh",
                                "qstat -x {0}"])

    def __init__(self, *args, **kwargs):
        super(SSHPBSProExecBackend, self).__init__(*args, **kwargs)
        self.parser = PBSProParser()

    def submit_task(self):
        logger.debug("SSHPBSProExecBackend.submit_task ...")
        qsub_result = self._run_qsub()

        if qsub_result.status == qsub_result.JOB_SUBMITTED:
            self.task.remote_id = qsub_result.remote_id
            self.task.save()
            logger.debug("Yabi Task %s submitted to PBSPro OK. remote id = %s" % (self.task.pk, self.task.remote_id))
        else:
            raise Exception("Error submitting remote job to PBSPro for yabi task %s remote job %s: %s" %
                            (self.task.pk, qsub_result.remote_id, qsub_result.error))

    def _run_qsub(self):
        exec_scheme, exec_parts = uriparse(self.task.job.exec_backend)
        working_scheme, working_parts = uriparse(self.working_output_dir_uri())
        submission_script_name = self._generate_remote_script_name()
        logger.debug("creating qsub script %s" % submission_script_name)
        submission_script_body = self.get_submission_script(exec_parts.hostname, working_parts.path)
        qsub_script_body = self.QSUB_TEMPLATE.format(submission_script_name, submission_script_body)
        logger.debug("qsub script:\n%s" % qsub_script_body)
        stdout, stderr = self._exec_script(qsub_script_body)
        logger.debug("pbspro qsub stdout lines = %s" % stdout)
        logger.debug("pbspro qsub stderr lines = %s" % stderr)
        qsub_result = self.parser.parse_qsub(stdout, stderr)
        return qsub_result


    def _get_polling_script(self):
        return self.QSTAT_TEMPLATE.format(self.task.remote_id)

    def _run_qstat(self):
        qstat_command = self._get_polling_script()
        stdout, stderr = self._exec_script(qstat_command)
        qstat_result = self.parser.parse_qstat(self.task.remote_id, stdout, stderr)
        return qstat_result

    def poll_task_status(self):
        qstat_result = self._run_qstat()

        if qstat_result.status == PBSProQStatResult.JOB_RUNNING:
            logger.debug("remote job %s for yabi task %s is stilling running" % (self.task.remote_id, self.task))
            # cause retry of polling task ( not sure if this is the best
            retry_ex = RetryException("remote job %s still running" % self.task.remote_id)
            retry_ex.backoff_strategy = RetryException.BACKOFF_STRATEGY_CONSTANT
            raise retry_ex

        elif qstat_result.status == PBSProQStatResult.JOB_NOT_FOUND:
            logger.debug("qstat for remote job %s did not produce results" % self.task.remote_id)
            # For Torque this is an error
            raise Exception("Remote job %s for Yabi task %s not found by qstat" % (self.task.remote_id, self.task.pk))

        elif qstat_result.status == PBSProQStatResult.JOB_SUCCEEDED:
            logger.debug("yabi task %s succeeded" % self.task.pk)
            stdout, stderr = self._locate_stdout_and_stderr()

            STDOUT_FILE = os.path.join(self.working_output_dir_uri().path, "STDOUT.txt")
            STDERR_FILE = os.path.join(self.working_output_dir_uri().path, "STDERR.txt")
            self.local_copy(stdout, STDOUT_FILE)
            self.local_copy(stderr, STDERR_FILE)


        elif qstat_result.status == PBSProQStatResult.JOB_FAILED:
            logger.debug("remote job for yabi task %s failed" % self.task.pk)
            # how to cause a job resubmission?
            raise Exception("Yabi task %s failed remotely" % self.task.pk)
        else:
            raise Exception("Yabi task %s unknown state: %s" % (self.task.pk, qstat_result.status))

    def _locate_stdout_and_stderr(self):
        """
        @return: a pair of paths of stdout and stderr of the submitted (and run) job
        """
        remote_id = self.task.remote_id
        logger.debug("remote id = %s" % remote_id)
        submission_script_name = os.path.basename(self.task.job_identifier)
        logger.debug("submission script name = %s" % submission_script_name)
        backend_credential = fs_credential(self.yabiusername, self.working_dir_uri())

        remote_username = backend_credential.credential.username

        path = "/home/%s" % remote_username # location of the <jobname>.o<jobnumber> and <jobname>.e<jobnumber> files

        # gotcha - the script name gets truncated by the scheduler
        std_out_file = "{0}/{1}.o{2}".format(path, submission_script_name[:15], remote_id)
        std_err_file = "{0}/{1}.e{2}".format(path, submission_script_name[:15], remote_id)
        logger.debug("stdout file = %s" % std_out_file)
        logger.debug("stderr file = %s" % std_err_file)


        return stdout, stderr







