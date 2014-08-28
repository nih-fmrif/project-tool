#!/usr/bin/env python
import os
import sys
import pwd
import yaml
import shutil
import logging
import argparse

# pylibacl 0.5.2 from PyPi (pip install pylibacl - need python-devel,libacl-devel)
import posix1e

DEBUG = False
PROJECT_ROOT = os.path.realpath(os.path.expanduser(
        os.environ.get('PROJECT_ROOT', '/fmrif/projects')))
OWNER_ROLE = "owner"
MEMBER_ROLE = "member"
COLLAB_ROLE = "collaborator"
ROLE_NAMES = [OWNER_ROLE, MEMBER_ROLE, COLLAB_ROLE]

logger = logging.getLogger(__name__)

class ColorFormatter(logging.Formatter):
    black, red, green, yellow, blue, magenta, cyan, white = 0, 1, 2, 3, 4, 5, 6, 7
    colors = { 'WARNING': yellow, 'INFO': blue, 'DEBUG': green, 'CRITICAL': magenta, 'ERROR': red }
    def format(self, record):
        record.levelname = "\033[1;%dm%s\033[0m" % (
                30 + ColorFormatter.colors[record.levelname], record.levelname)
        # can't use `super` here because Formatter is not a 'new-style' class
        return logging.Formatter.format(self, record)

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

    def save(self):
        """Writes a project YAML config file to disk."""
        stuff = {
            "public":self.public,
            "owner":self.owner,
            "members":self.members,
            "collaborators":self.collaborators
        }
        with open(project_conf_path(self.project), 'w') as fobj:
            fobj.write(yaml.dump(stuff, default_flow_style=False))

def load_conf(project_name):
    """ Reads a project YAML config file and returns a ProjectDB instance."""
    with open(project_conf_path(project_name)) as fobj:
        loaded = yaml.load(fobj.read())
    conf = ProjectDB(project_name, loaded['owner'], loaded['public'],
            loaded['members'], loaded['collaborators'])
    return conf

def main():
    global DEBUG, PROJECT_ROOT
    parser = argparse.ArgumentParser(
            prog="project",
            description="Manage projects",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-P", "--project-root", metavar="<root>",
            help="project root directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    parser.add_argument("-d", "--debug", action="store_true",  help="enable debug mode")
    parser.add_argument("--nocolor", action="store_true",  help="enable colors")
    parser.set_defaults(project_root=PROJECT_ROOT,)

    subparsers = parser.add_subparsers(title="commands", dest="which",
            metavar="<command>")

    parent_parser = argparse.ArgumentParser(add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parent_parser.add_argument("project", help="name of project")

    list_parser = subparsers.add_parser("list",
            help="list projects",
            epilog="Lists all projects to which you have access",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    list_parser.add_argument("-a", "--all", action="store_true",
            help="list ALL projects in PROJECT_ROOT")
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

    # set up loggin (i.e. fancy console output)
    console = logging.StreamHandler()
    formatter = logging.Formatter if args.nocolor else ColorFormatter
    console.setFormatter(formatter("%(levelname)s: %(message)s"))
    console.setLevel(logging.DEBUG)
    logger.addHandler(console)

    if args.verbose:
        logger.setLevel(logging.INFO)
    elif args.debug:
        DEBUG = True
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    if args.which == 'help':
        try:
            subp = subparsers.choices[args.command]
        except KeyError:
            logger.error("Invalid command: %s" % args.command)
        else:
            subp.print_help()
        sys.exit(0)

    # determine username of user running this program (Unix)
    args.executer = pwd.getpwuid(os.getuid()).pw_name
    logger.debug("You are: %s" % args.executer)

    if not os.path.isdir(args.project_root):
        logger.error("Project root %s is not a directory." % args.project_root)
    PROJECT_ROOT = args.project_root
    logger.info("PROJECT_ROOT: %s" % PROJECT_ROOT)

    args.func(args)


def fail(msg):
    logger.error(msg)
    sys.exit(1)

def list_projects(args):
    projects = []
    for dirname in os.listdir(PROJECT_ROOT):
        pdir = os.path.join(PROJECT_ROOT, dirname)
        pconf = project_conf_path(dirname)
        if not os.path.isdir(pdir):
            logger.debug("Unknown project: %s" % pdir)
            continue
        if not os.path.isfile(pconf):
            logger.debug("Unknown config file: %s" % pconf)
            continue
        projname = dirname
        if args.all:
            projects.append(projname)
        else:
            # only append projects for which user has access
            try:
                conf = load_conf(projname)
            except IOError:
                continue    # no permission to read YAML
            users = [conf.owner] + conf.members + conf.collaborators
            for username in users:
                if args.executer == username:
                    projects.append(projname)

    for proj in projects:
        print(' ' * 4 + proj)

def create_project(args):
    pdir = project_dir_path(args.project)
    pconf = project_conf_path(args.project)
    if os.path.isdir(pdir):
        fail("Project directory '%s' already exists" % pdir)
    if os.path.isfile(pconf):
        fail("Project config '%s' already exists" % pconf)

    logger.info("Creating directory: %s" % pdir)
    try:
        os.mkdir(pdir)
    except OSError as e:
        fail(e)
    logger.info("Creating config file: %s" % pconf)
    conf = ProjectDB(args.project, args.executer, args.public)

    # this is the only place where we save the project config BEFORE updating permissions
    conf.save()
    update_perms(conf)

def delete_project(args):
    check_project_exists(args.project)

    conf = load_conf(args.project)
    if conf.owner != args.executer:
        fail("Only the project owner can delete a project")

    logger.debug("Removing project directory")
    shutil.rmtree(project_dir_path(args.project))
    logger.debug("Removing project config file")
    os.remove(project_conf_path(args.project))

def print_info(args):
    check_project_exists(args.project)
    conf = load_conf(args.project)
    print(conf)

def refresh_permissions(args):
    check_project_exists(args.project)
    conf = load_conf(args.project)

    if args.executer in conf.members or args.executer == conf.owner:
        update_perms(conf)
    else:
        fail("Only a project owner/member may update its permissions")

def update_perms(conf):
    pdir = project_dir_path(conf.project)
    pconf = project_conf_path(conf.project)

    logger.info("Chown project directory: %s" % pdir)
    os.chown(pdir, os.getuid(), os.getgid())
    logger.info("Recursively updating ACL on project directory")
    set_access(pdir, conf.owner, conf.members, conf.collaborators, conf.public)

    logger.info("Chown project config file: %s" % pconf)
    os.chown(pconf, os.getuid(), os.getgid())
    logger.info("Updating ACL on project config file")
    set_access(pconf, conf.owner, [], [], conf.public)

    # save the config file on disk
    conf.save()

def is_subdir(path, subdir):
    """Tested in `test_project_manager.py` but be wary"""
    path = os.path.realpath(os.path.expanduser(path))
    subdir = os.path.realpath(os.path.expanduser(subdir))
    if subdir == path:
        return True
    elif subdir == '/':
        return False
    return is_subdir(path, os.path.dirname(subdir))

def set_access(root, owner, read_write, read_only, public):
    """
    Recursively change the owner of all files to the current user, since
    only a file's owner can set its ACL.
    Clear and reset the ACL for each file/directory in the project.
    Recursively change the owner of all files to the project's owner.
    """
    # Don't allow top-level files/dirs to be symbolic links
    if os.path.islink(root):
        fail("%s is a symbolic link. Cannot update ACL")

    acl_text = 'u::rwx,g::rwx'
    if public:
        acl_text += ',o::r-x'
    else:
        acl_text += ',o::---'

    # Owners and Members have read/write
    writers = read_write + [owner]
    for user in writers:
        acl_text += ',u:%s:rwx' % user
    # Collaborators have read-only
    for user in read_only:
        acl_text += ',u:%s:r-x' % user

    acl = posix1e.ACL(text=acl_text)
    acl.calc_mask()

    if not acl.valid():
        logger.debug("Bad ACL: %s" % acl_text)
        fail("Error generating ACL. Please notify system administrator.")

    apply_acl(root, acl)

    for top, dirs, files in os.walk(root):
        for name in dirs + files:
            path = os.path.join(top, name)
            realpath = os.path.realpath(os.path.expanduser(path))
            if is_subdir(PROJECT_ROOT, realpath):
                apply_acl(path, acl)
            else:
                logger.warning(
                        "%s is actually %s, which is not in $PROJECT_ROOT" %
                        (path, realpath))

def apply_acl(path, acl):
    logger.debug("Applying ACL to %s" % path)
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
        # "Look up" user
        pwd.getpwnam(args.username)
    except KeyError:
        fail("User %s is not a valid user" % args.username)

    conf = load_conf(args.project)

    if args.executer != conf.owner and args.executer not in conf.members:
        fail("Only a project owner/member can add/modify users")

    if args.username == conf.owner:
        if args.role != "owner":
            fail("Can't remove permissions from owner. Set a new owner first")
        else:
            fail("Already project owner")
    elif args.username in conf.members:
        if args.role != MEMBER_ROLE:
            logger.info("Removing %s from members" % args.username)
            conf.members.remove(args.username)
        else:
            fail("Already a member")
    elif args.username in conf.collaborators:
        if args.role != COLLAB_ROLE:
            logger.info("Removing %s from collaborators" % args.username)
            conf.collaborators.remove(args.username)
        else:
            fail("Already a collaborator")

    if args.role == "owner":
        prev_owner = conf.owner
        logger.info("Setting %s as new owner" % args.username)
        conf.owner = args.username
        logger.info("Demoting previous owner %s" % prev_owner)
        conf.members.append(prev_owner)
    elif args.role == MEMBER_ROLE:
        logger.info("Setting %s as member" % args.username)
        conf.members.append(args.username)
    elif args.role == COLLAB_ROLE:
        logger.info("Setting %s as collaborator" % args.username)
        conf.collaborators.append(args.username)

    update_perms(conf)

def del_user(args):
    check_project_exists(args.project)
    try:
        # "Look up" user
        pwd.getpwnam(args.username)
    except KeyError:
        fail("User %s is not a valid user" % args.username)

    conf = load_conf(args.project)

    if args.executer != conf.owner and args.executer not in conf.members:
        fail("Only a project owner/member can delete users")

    if args.username == conf.owner:
        fail("Can't delete owner. Set a new owner first")
    if args.username in conf.members:
        logger.info("Removing %s from members" % args.username)
        conf.members.remove(args.username)
    if args.username in conf.collaborators:
        logger.info("Removing %s from members" % args.username)
        conf.collaborators.remove(args.username)

    update_perms(conf)

def check_project_exists(project_name):
    d = project_dir_path(project_name)
    c = project_conf_path(project_name)
    if not os.path.isdir(d):
        fail("Project directory '%s' does not exist. %s is not a project" %
                (d, project_name))
    if not os.path.isfile(c):
        fail("Project config '%s' does not exist. %s is not a project" % (
            c, project_name))

def project_dir_path(project_name):
    """
    Constructs the path to a project's directory
    """
    return os.path.join(PROJECT_ROOT, project_name)

def project_conf_path(project_name):
    """Dynamically forms a project's user config file path
    Modify this function if you change the location of a project's DB.
    Constructs the path to a project's YAML config file
    """
    return os.path.join(PROJECT_ROOT, ".%s.yml" % project_name)


if __name__ == "__main__":
    main()
