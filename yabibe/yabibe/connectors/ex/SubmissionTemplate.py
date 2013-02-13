#!/usr/bin/env python
#
# Mako templating support functions for submission script templating

from mako.template import Template

def make_script(template,working,command,modules,cpus,memory,walltime,yabiusername,username,host,queue,stdout,stderr,tasknum,tasktotal):
    cleaned_template = template.replace('\r\n','\n').replace('\n\r','\n').replace('\r','\n')
    tmpl = Template(cleaned_template)
    
    # our variable space
    variables = {
        'working':working,
        'command':command,
        'modules':modules,
        'cpus':cpus,
        'memory':memory,
        'walltime':walltime,
        'yabiusername':yabiusername,
        'username':username,
        'host':host,
        'queue':queue,
        'stdout':stdout,
        'stderr':stderr,
        'tasknum':tasknum,
        'tasktotal':tasktotal,
        'arrayid':tasknum,
        'arraysize':tasktotal
    }
    
    return str(tmpl.render(**variables))
    
class Submission(object):
    """Handle the rendering and holding of a submission script"""
    
    def __init__(self, submission):
        self.submission = submission
        self.cleaned_template = submission.replace('\r\n','\n').replace('\n\r','\n').replace('\r','\n')
        self.template = Template(self.cleaned_template)
    
    def render(self, kwargs=None):
        """call with kwargs to render the result,
        Call with no argument to return last rendered result (or exception if its never been rendered"""
        if kwargs is not None:
            self.rendered = str( self.template.render(**kwargs) )
        return self.rendered
        