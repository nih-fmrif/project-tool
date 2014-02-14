#!/usr/bin/env python
import os
import sys
import pwd
import yaml
import shutil
import argparse

# pylibacl 0.5.1 (http://pylibacl.k1024.org/ or https://github.com/iustin/pylibacl)
import posix1e


PROJECT_ROOT = os.environ.get('PROJECT_ROOT', '/fmrif/projects')
OWNER_ROLE = "owner"
MEMBER_ROLE = "member"
COLLAB_ROLE = "collaborator"
ROLE_NAMES = [OWNER_ROLE, MEMBER_ROLE, COLLAB_ROLE]


class ProjectDB(object):
    def __init__(self, project, owner, public=False, members=[], collaborators=[]):
        self.project = project
        self.public = public
        self.owner = owner
        self.members = members
        self.collaborators = collaborators

    def __str__(self):
        s = "Owner: %s\n" % self.owner
        s += "Members:\n"
        for man in self.members:
            s += "\t%s\n" % man
        s += "Collaborators:\n"
        for col in self.collaborators:
            s += "\t%s\n" % col
        s += "Public: %s" % self.public
        return s

def main():
    global PROJECT_ROOT
    parser = argparse.ArgumentParser(
            prog="project",
            description="Manage projects",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-P", "--project-root", metavar="<root>",
            help="project root directory")
    parser.set_defaults(project_root=PROJECT_ROOT,)

    subparsers = parser.add_subparsers(title="commands", dest="which",
            metavar="<command>")

    parent_parser = argparse.ArgumentParser(add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parent_parser.add_argument("project", help="name of project")

    list_parser = subparsers.add_parser("list",
            help="list all projects",
            epilog="Lists all projects found in PROJECT_ROOT",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    list_parser.set_defaults(func=list_projects)

    create_parser = subparsers.add_parser("create",
            help="create new project",
            epilog="Note that projects are 'private' by default",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    create_parser.add_argument("--public", action="store_true",
            help="make project publicly readable")
    create_parser.set_defaults(func=create_project)

    delete_parser = subparsers.add_parser("delete",
            help="delete existing project",
            epilog="This will permanently delete the project directory!",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    delete_parser.set_defaults(func=delete_project)

    info_parser = subparsers.add_parser("info",
            help="print information about project",
            epilog="Prints information about a project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    info_parser.set_defaults(func=print_info)

    update_parser = subparsers.add_parser("update",
            help="update permissions on project",
            epilog="Updates the permissions on everything in the project directory.",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    update_parser.set_defaults(func=refresh_permissions)

    user_parser = argparse.ArgumentParser(add_help=False,
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    user_parser.add_argument("username", help="user's UNIX username")
    user_parser.add_argument("role", choices=ROLE_NAMES,
            #metavar="role",
            help="new user role")

    add_user_parser = subparsers.add_parser("adduser",
            help="add user to project",
            parents=[user_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    add_user_parser.set_defaults(func=mod_user)

    mod_user_parser = subparsers.add_parser("moduser",
            help="modify user permissions",
            parents=[user_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    mod_user_parser.set_defaults(func=mod_user)

    del_user_parser = subparsers.add_parser("deluser",
            help="remove user from project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    del_user_parser.add_argument("username", help="user's UNIX username")
    del_user_parser.set_defaults(func=del_user)

    help_parser = subparsers.add_parser('help',
            help="print help info for command",
            epilog="Prints the help information for the given command.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    help_parser.add_argument("command", help="project command")

    args = parser.parse_args()

    if args.which == 'help':
        try:
            subp = subparsers.choices[args.command]
        except KeyError:
            print("Invalid command: %s" % args.command)
        else:
            subp.print_help()
        sys.exit(0)

    # determine username of user running this program (Unix)
    args.executer = pwd.getpwuid(os.getuid()).pw_name

    if not os.path.isdir(args.project_root):
        parser.error("Project root %s is not a directory." % args.project_root)
    PROJECT_ROOT = args.project_root

    args.func(args)


def fail(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

def list_projects(args):
    projs = []
    for dirname in os.listdir(PROJECT_ROOT):
        pdir = os.path.join(PROJECT_ROOT, dirname)
        pconf = project_conf_path(dirname)
        if os.path.isdir(pdir) and os.path.isfile(pconf):
            projs.append(dirname)
    for proj in projs:
        print(' '*4 + proj)

def create_project(args):
    pdir = project_dir_path(args.project)
    pconf = project_conf_path(args.project)
    if os.path.isdir(pdir):
        fail("Project directory '%s' already exists" % pdir)
    if os.path.isfile(pconf):
        fail("Project config '%s' already exists" % pconf)

    os.mkdir(pdir)
    os.chown(pdir, os.getuid(), os.getgid())

    conf = ProjectDB(args.project, args.executer, args.public)
    write_project_conf_path(conf)
    update_perms(conf)
    os.chown(pconf, os.getuid(), os.getgid())

def delete_project(args):
    check_project_exists(args.project)

    conf = read_project_conf_path(args.project)
    if conf.owner != args.executer:
        fail("Only the project owner can delete a project")

    shutil.rmtree(project_dir_path(args.project))
    os.remove(project_conf_path(args.project))

def print_info(args):
    check_project_exists(args.project)
    conf = read_project_conf_path(args.project)
    print(conf)

def refresh_permissions(args):
    check_project_exists(args.project)
    conf = read_project_conf_path(args.project)

    if (args.executer not in conf.members and args.executer not in conf.collaborators
            and args.executer != conf.owner):
        fail("Only a project member may update the project's permissions")

    update_perms(conf)

def update_perms(conf):
    # Yuck, specifying individual project directories here
    pdir = project_dir_path(conf.project)
    set_access(pdir, conf.owner, conf.members, conf.collaborators, conf.public)
    set_access(project_conf_path(conf.project), conf.owner, [], [], conf.public)

def set_access(root, owner, read_write, read_only, public):
    """
    Recursively change the owner of all files to the current user, since
    only a file's owner can set its ACL.
    Clear and reset the ACL for each file/directory in the project.
    Recursively change the owner of all files to the project's owner.
    """

    # Owner always has read/write permissions
    read_write.append(owner)

    acl_text = 'u::rwx,g::rwx'
    if public:
        acl_text += ',o::r-x'
    else:
        acl_text += ',o::---'

    for user in read_write:
        acl_text += ',u:%s:rwx' % user
    for user in read_only:
        acl_text += ',u:%s:r-x' % user

    acl = posix1e.ACL(text=acl_text)
    acl.calc_mask()

    if not acl.valid():
        fail("Error generating ACL. Please notify system administrator.")

    apply_acl(root, acl)

    for top, dirs, files in os.walk(root):
        for d in dirs:
            path = os.path.join(top, d)
            apply_acl(path, acl)
        for f in files:
            path = os.path.join(top, f)
            apply_acl(path, acl)

def apply_acl(path, acl):
    if os.path.isdir(path):
        try:
            posix1e.delete_default(path)
        except:
            fail("Can't reset ACL on directory: %s" % path)
        try:
            acl.applyto(path, posix1e.ACL_TYPE_DEFAULT)
        except:
            fail("Can't update ACL on directory: %s" % path)
    try:
        acl.applyto(path)
    except:
        fail("Can't update ACL on file: %s" % path)

def mod_user(args):
    check_project_exists(args.project)

    try:
        pwd.getpwnam(args.username)
    except KeyError:
        fail("User %s is not a valid user" % args.username)

    conf = read_project_conf_path(args.project)

    if args.executer != conf.owner and args.executer not in conf.members:
        fail("Only a project owner/member can add/modify users")

    if args.username == conf.owner:
        if args.role != "owner":
            fail("Can't remove permissions from owner. Set a new owner first")
        else:
            fail("Already project owner")
    if args.username in conf.members:
        if args.role != MEMBER_ROLE:
            conf.members.remove(args.username)
        else:
            fail("Already a member")
    if args.username in conf.collaborators:
        if args.role != COLLAB_ROLE:
            conf.collaborators.remove(args.username)
        else:
            fail("Already a collaborator")

    if args.role == "owner":
        conf.owner = args.username
    elif args.role == MEMBER_ROLE:
        conf.members.append(args.username)
    elif args.role == COLLAB_ROLE:
        conf.collaborators.append(args.username)

    write_project_conf_path(conf)
    update_perms(conf)

def del_user(args):
    check_project_exists(args.project)

    try:
        pwd.getpwnam(args.username)
    except KeyError:
        fail("User %s is not a valid user" % args.username)

    conf = read_project_conf_path(args.project)

    if args.executer != conf.owner and args.executer not in conf.members:
        fail("Only a project owner/member can delete users")

    if args.username == conf.owner:
        fail("Can't delete owner. Set a new owner first")
    if args.username in conf.members:
        conf.members.remove(args.username)
    if args.username in conf.collaborators:
        conf.collaborators.remove(args.username)

    write_project_conf_path(conf)
    update_perms(conf)

def check_project_exists(project_name):
    d = project_dir_path(project_name)
    c = project_conf_path(project_name)
    if not os.path.isdir(d):
        fail("Project directory '%s' does not exist" % d)
    if not os.path.isfile(c):
        fail("Project config '%s' does not exist" % c)

def project_dir_path(project_name):
    """
    Constructs the path to a project's directory
    """
    return os.path.join(PROJECT_ROOT, project_name)

def project_conf_path(project_name):
    """Dynamically forms a project's user database path
    Modify this function if you change the location of a project's DB.
    Constructs the path to a project's YAML config file
    """
    return os.path.join(PROJECT_ROOT, ".%s.yml" % project_name)

def write_project_conf_path(conf):
    """Writes a project YAML config file to disk."""
    stuff = {
        "public":conf.public,
        "owner":conf.owner,
        "members":conf.members,
        "collaborators":conf.collaborators
    }
    with open(project_conf_path(conf.project), 'w') as fobj:
        fobj.write(yaml.dump(stuff, default_flow_style=False))

def read_project_conf_path(project_name):
    """ Reads a project YAML config file and returns a ProjectDB instance."""
    with open(project_conf_path(project_name)) as fobj:
        loaded = yaml.load(fobj.read())
    conf = ProjectDB(project_name, loaded['owner'], loaded['public'],
            loaded['members'], loaded['collaborators'])
    return conf


if __name__ == "__main__":
    main()
