#!/usr/bin/env python
#
# Mako templating support functions for submission script templating

from mako.template import Template

def make_script(template, working, command, modules, cpus, memory, walltime, 
                yabiusername, username, host, queue, stdout, stderr, tasknum,
                tasktotal):
    make_script(template, 
              working=working, command=command, modules=modules, cpus=cpus,
              memory=memory, walltime=walltime, yabiusername=yabiusername,
              username=username, host=host, queue=queue, stdout=stdout,
              stderr=stderr, tasknum=tasknum, tasktotal=tasktotal)

def make_script(template, **kwargs):
    cleaned_template = template.replace('\r\n', '\n').replace('\n\r', '\n').replace('\r', '\n')
    tmpl = Template(cleaned_template)

    # our variable space
    variables = kwargs.copy()
    make_alias(kwargs, 'tasknum', 'arrayid')
    make_alias(kwargs, 'tasktotal', 'arraysize')

    return str(tmpl.render(**variables))


def make_alias(variables, name, alias):
    "Receives a map of name, values. Creates an alias for name in the map"
    if variables.has_key(name):
         variables[alias] = variables['name']
