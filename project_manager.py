#!/usr/bin/env python2
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
    parent_parser.add_argument("project", metavar="project-name", help="name of project")

    list_parser = subparsers.add_parser("list",
            help="list projects",
            epilog="Lists all projects to which you have access",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    list_parser.add_argument("-a", "--all", action="store_true",
            help="list ALL projects in PROJECT_ROOT")
    list_parser.set_defaults(func=list_projects)

    check_parser = subparsers.add_parser("check",
            help="check project permissions",
            epilog="Checks the permissions on all projects to which you have access",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    check_parser.add_argument("-a", "--all", action="store_true",
            help="check ALL projects in PROJECT_ROOT")
    check_parser.set_defaults(func=check_projects)

    create_parser = subparsers.add_parser("create",
            help="create new project",
            epilog="Note that projects are 'private' by default",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    create_parser.add_argument("--public", action="store_true",
            help="make project publicly readable")
    create_parser.set_defaults(func=create_project)

    rename_parser = subparsers.add_parser("rename",
            help="rename project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    rename_parser.add_argument("new_name", metavar="new-name", help="new name for project")
    rename_parser.set_defaults(func=rename_project)

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
            epilog="Updates file permissions on the entire project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    update_parser.set_defaults(func=refresh_permissions)

    user_parser = argparse.ArgumentParser(add_help=False,
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    user_parser.add_argument("role", choices=ROLE_NAMES,
            #metavar="role",
            help="new user role")
    user_parser.add_argument("username", nargs='+', help="user's UNIX username")

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
    del_user_parser.add_argument("username", nargs='+', help="user's UNIX username")
    del_user_parser.set_defaults(func=del_user)

    help_parser = subparsers.add_parser('help',
            help="print help info for command",
            epilog="Prints the help information for the given command.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    help_parser.add_argument("command", nargs='?', default=None, help="project command")

    args = parser.parse_args()

    # set up logging (i.e. fancy console output)
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
        # print main help
        if args.command is None:
            parser.print_help()
        else:
            try:
                subp = subparsers.choices[args.command]
                subp.print_help()
            except KeyError:
                logger.error("Invalid command: %s" % args.command)
                sys.exit(1)
        sys.exit(0)

    # determine username of user running this program (Unix)
    args.executer = pwd.getpwuid(os.getuid()).pw_name
    logger.debug("You are: %s" % args.executer)

    if not os.path.isdir(args.project_root):
        logger.error("Project root %s is not a directory." % args.project_root)
    PROJECT_ROOT = args.project_root
    logger.info("PROJECT_ROOT: %s" % PROJECT_ROOT)

    # strip all preceding directories from project name
    # e.g. if user typed full path to project
    if hasattr(args, 'project'):
        args.project = os.path.basename(args.project)

    # dispatch to user-specified command
    args.func(args)


def fail(msg):
    logger.error(msg)
    sys.exit(1)

def projects_for_user(username, all=False):
    """ Yields each project name user `username` has access to,
    or all project names if `all` is True."""
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
        if all:
            yield projname
        else:
            # only yield projects for which user has access
            try:
                conf = load_conf(projname)
            except IOError:
                continue    # no permission to read YAML
            users = [conf.owner] + conf.members + conf.collaborators
            if username in users:
                yield projname

def list_projects(args):
    """ Prints the name of each project the user has access to,
    or all projects if `args.all` is True."""
    for proj in projects_for_user(args.executer, args.all):
        print(' ' * 4 + proj)

def check_projects(args):
    for proj in projects_for_user(args.executer, args.all):
        pdir = project_dir_path(proj)
        pconf = project_conf_path(proj)
        conf = load_conf(proj)

        # check ACL on project config file
        acl = posix1e.ACL(file=pconf)
        if not acl.valid():
            print("Project %s needs fixed, invalid ACL" % conf.project)
            continue
        text = acl.to_any_text()
        if 'user:%s:rwx' % conf.owner not in text:
            print("Project %s needs fixed, owner doesn't have permissions" % conf.project)
            continue

        # check access ACL on project directory
        acl = posix1e.ACL(file=pdir)
        if not _check_acl(acl, conf):
            continue
        # check default ACL on project directory
        acl = posix1e.ACL(filedef=pdir)
        if not _check_acl(acl, conf):
            continue

def _check_acl(acl, conf):
    def member(u): return 'user:%s:rwx' % u
    def collab(u): return 'user:%s:r-x' % u
    public = 'other::r-x'
    private = 'other::---'

    if not acl.valid():
        print("Project %s needs fixed, invalid ACL" % conf.project)
        return False
    text = acl.to_any_text()
    if not member(conf.owner) in text:
        print("Project %s needs fixed, owner doesn't have permissions" % conf.project)
        return False
    for m in conf.members:
        if not member(m) in text:
            print("Projects %s needs fixed, %s doesn't have permissions" % m)
            return False
    for c in conf.collaborators:
        if not collab(c) in text:
            print("Project %s needs fixed, %s doesn't have permissions" % c)
            return False

    if conf.public and not public in text:
        print("Project %s needs fixed, world doesn't have access" % conf.project)
        return False
    elif not conf.public and not private in text:
        print("Project %s needs fixed, world access not blocked" % conf.project)
        return False

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

def rename_project(args):
    check_project_exists(args.project)

    conf = load_conf(args.project)
    if conf.owner != args.executer:
        fail("Only the project owner can rename a project")

    # strip directories from new project name
    args.new_name = os.path.basename(args.new_name)

    new_project_dir = project_dir_path(args.new_name)
    new_project_conf = project_conf_path(args.new_name)
    logger.debug("Renaming project directory")
    os.rename(project_dir_path(args.project), new_project_dir)
    logger.debug("Renaming project config file")
    os.rename(project_conf_path(args.project), new_project_conf)

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
    """ Display the contents of a project's configuration file."""
    check_project_exists(args.project)
    conf = load_conf(args.project)
    print(conf)

def refresh_permissions(args):
    """ Refresh the permissions on a project.

    Note: anyone can refresh the permissions on any project because
    the operation does not affect the project's owner/members/etc.
    """
    check_project_exists(args.project)
    conf = load_conf(args.project)
    update_perms(conf)

def update_perms(conf):
    """ Sets the UNIX owner/group of the project directory/config to the owner
    of the project (chown). Recursively sets the ACLs on the config and entire
    project directory.
    """
    pdir = project_dir_path(conf.project)
    pconf = project_conf_path(conf.project)

    uid, gid = 0, 0
    try:
        pw = pwd.getpwnam(conf.owner)
        uid = pw.pw_uid
        gid = pw.pw_gid
    except KeyError:
        fail("Failed to lookup user information for owner")

    logger.info("Chown project directory: %s" % pdir)
    try:
        os.chown(pdir, uid, gid)
    except OSError:
        fail("Failed to chown project directory")

    logger.info("Chown project config file: %s" % pconf)
    try:
        os.chown(pconf, uid, gid)
    except OSError:
        fail("Failed to chown project config file")

    # first update ACL on project config
    logger.info("Updating ACL on project config file")
    set_access(pconf, conf.owner, [], [], conf.public)

    # update ACL on project directory and files
    logger.info("Recursively updating ACL on project directory")
    set_access(pdir, conf.owner, conf.members, conf.collaborators, conf.public)

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
    Recursively changes the owner of all files to the current user, since
    only a file's owner can set its ACL.
    Clears and resets the ACL for each file/directory in the project.
    Recursively changes the owner of all files to the project's owner.
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

    try:
        acl = posix1e.ACL(text=acl_text)
    except:
        fail("Failed to create ACL. Check project config file for non-existent users")
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
    conf = load_conf(args.project)

    if args.executer != conf.owner and args.executer not in conf.members:
        fail("Only a project owner/member can add/modify users")

    for username in args.username:
        try:
            # "Look up" user
            pwd.getpwnam(username)
        except KeyError:
            fail("User %s is not a valid user" % username)

        if username == conf.owner:
            if args.role != "owner":
                fail("Can't remove permissions from owner. Set a new owner first")
            else:
                fail("Already project owner")
        elif username in conf.members:
            if args.role != MEMBER_ROLE:
                logger.info("Removing %s from members" % username)
                conf.members.remove(username)
            else:
                fail("Already a member")
        elif username in conf.collaborators:
            if args.role != COLLAB_ROLE:
                logger.info("Removing %s from collaborators" % username)
                conf.collaborators.remove(username)
            else:
                fail("Already a collaborator")

        if args.role == "owner":
            prev_owner = conf.owner
            logger.info("Setting %s as new owner" % username)
            conf.owner = username
            logger.info("Demoting previous owner %s" % prev_owner)
            conf.members.append(prev_owner)
        elif args.role == MEMBER_ROLE:
            logger.info("Setting %s as member" % username)
            conf.members.append(username)
        elif args.role == COLLAB_ROLE:
            logger.info("Setting %s as collaborator" % username)
            conf.collaborators.append(username)

    update_perms(conf)

def del_user(args):
    check_project_exists(args.project)
    conf = load_conf(args.project)

    if args.executer != conf.owner and args.executer not in conf.members:
        fail("Only a project owner/member can delete users")

    for username in args.username:
        try:
            # "Look up" user
            pwd.getpwnam(username)
        except KeyError:
            fail("User %s is not a valid user" % username)

        if username == conf.owner:
            fail("Can't delete owner. Set a new owner first")
        if username in conf.members:
            logger.info("Removing %s from members" % username)
            conf.members.remove(username)
        if username in conf.collaborators:
            logger.info("Removing %s from members" % username)
            conf.collaborators.remove(username)

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
    """ Constructs the path to a project's directory. """
    return os.path.join(PROJECT_ROOT, project_name)

def project_conf_path(project_name):
    """Dynamically forms a project's user config file path
    Modify this function if you change the location of a project's DB.
    Constructs the path to a project's YAML config file
    """
    return os.path.join(PROJECT_ROOT, ".%s.yml" % project_name)


if __name__ == "__main__":
    main()
