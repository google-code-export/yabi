from django.db import models
from yabiadmin.yabmin.models import User

class Workflow(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    json = models.TextField(blank=True)
    log_file_path = models.CharField(max_length=1000,null=True)
    last_modified_on = models.DateTimeField(null=True, auto_now=True, editable=False)
    created_on = models.DateTimeField(auto_now_add=True, editable=False)

    def __unicode__(self):
        return self.name

class Job(models.Model):
    workflow = models.ForeignKey(Workflow)
    order = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    cpus = models.IntegerField(null=True)
    walltime = models.IntegerField(null=True)
    stageout = models.CharField(max_length=1000, null=True)

class Subjob(models.Model):
    job = models.ForeignKey(Job)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    job_identifier = models.TextField()
    command = models.TextField(blank=True)
    error_msg = models.CharField(max_length=1000, null=True)

class StageIn(models.Model):
    src_backend = models.CharField(max_length=256)
    src_path = models.TextField()
    dst_backend = models.CharField(max_length=256)
    dst_path = models.TextField()
    order = models.IntegerField()
    subjob = models.ForeignKey(Subjob)

class QueueBase(models.Model):
    class Meta:
        abstract = True

    workflow = models.ForeignKey(Workflow) 
    created_on = models.DateTimeField(auto_now_add=True)

    def name(self):
        return self.workflow.name

    def user_name(self):
        return self.workflow.user.name

class QueuedWorkflow(QueueBase):
    pass

class SysLog(models.Model):
    message = models.TextField(blank=True)
    table_name = models.CharField(max_length=64, null=True)
    table_id = models.IntegerField(null=True)
