#!/usr/bin/env python
import os
import yaml
from subprocess import Popen, PIPE

prefix = "/fmrif/projects"

paths = []
for name in os.listdir(prefix):
    if name.startswith('.') and name.endswith('.yml'):
        config = os.path.join(prefix, name)
        proj = name.replace('.yml', '').lstrip('.')
        project = os.path.join(prefix, proj)
        paths.append((config, project))


for conf, proj in paths:
    with open(conf, 'r') as f:
        config = yaml.load(f.read())

    p = Popen(['getfacl', proj], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    def member_access(u): return 'user:%s:rwx' % u
    def member_default(u): return 'default:user:%s:rwx' % u
    def collab_access(u): return 'user:%s:r-x' % u
    def collab_default(u): return 'default:user:%s:r-x' % u
    public_access = 'other::r-x'
    public_default = 'default:other::r-x'
    private_access = 'other::---'
    private_default = 'default:other::---'

    if not member_access(config['owner']) in out:
            print("Project %s needs fixed, owner doesn't have perms" % os.path.basename(proj))
            continue
    for member in config['members']:
        if not member_access(member) in out:
            print("Project %s needs fixed, %s doesn't have perms" % (os.path.basename(proj), member))
            continue
        if not member_default(member) in out:
            print("Project %s needs fixed, %s doesn't have perms" % (os.path.basename(proj), member))
            continue
    for collab in config['collaborators']:
        if not collab_access(collab) in out:
            print("Project %s needs fixed, %s doesn't have perms" % (os.path.basename(proj), collab))
            continue
        if not collab_default(collab) in out:
            print("Project %s needs fixed, %s doesn't have perms" % (os.path.basename(proj), collab))
            continue

    if config['public']:
        if not public_access in out:
            print("Project %s needs fixed, world doesn't have access" % os.path.basename(proj))
            continue
        if not public_default in out:
            print("Project %s needs fixed, world doesn't have access" % os.path.basename(proj))
            continue
    else:
        if not private_access in out:
            print("Project %s needs fixed, world access not blocked" % os.path.basename(proj))
            continue
        if not private_default in out:
            print("Project %s needs fixed, world access not blocked" % os.path.basename(proj))
            continue
