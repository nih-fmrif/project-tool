#!/usr/bin/env python
import os
import sys
import pwd
import yaml
import shutil
import argparse
import subprocess

# pylibacl 0.5.1 (http://pylibacl.k1024.org/ or https://github.com/iustin/pylibacl)
import posix1e


PROJECT_ROOT = "/fmrif"
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

    subparsers = parser.add_subparsers(title="commands", dest="which",
            metavar="<command>")

    parent_parser = argparse.ArgumentParser(add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parent_parser.add_argument("project", help="name of project")
    parent_parser.add_argument("-P", "--project-root", metavar="<root>",
            help="project root directory")
    parent_parser.set_defaults(project_root=PROJECT_ROOT,)

    create_parser = subparsers.add_parser("create",
            help="create new project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    create_parser.add_argument("--public", action="store_true",
            help="make project publicly readable")
    create_parser.set_defaults(func=create_project)

    delete_parser = subparsers.add_parser("delete",
            help="delete existing project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    delete_parser.set_defaults(func=delete_project)

    info_parser = subparsers.add_parser("info",
            help="print information about project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    info_parser.set_defaults(func=print_info)

    refresh_parser = subparsers.add_parser("refresh",
            help="refresh permissions on project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    refresh_parser.set_defaults(func=refresh_permissions)

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
    add_user_parser.set_defaults(func=mod_user, role="collaborator")

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

    args = parser.parse_args()

    # determine username of user running this program (Unix)
    args.executer = pwd.getpwuid(os.getuid()).pw_name

    if not os.path.isdir(args.project_root):
        parser.error("Project root %s is not a directory." % args.project_root)
    PROJECT_ROOT = args.project_root

    if not args.project.isalnum():
        parser.error("Project name must be alphanumeric.")

    args.func(args)

def fail(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

def create_project(args):
    for path in project_dirs(args.project).values():
        if os.path.isdir(path):
            fail("Project directory '%s' already exists" % path)
    if os.path.isfile(project_db_path(args.project)):
        fail("Project user database already exists")

    for path in project_dirs(args.project).values():
        os.mkdir(path)
        os.chown(path, os.getuid(), os.getgid())
    db = ProjectDB(args.project, args.executer, args.public)
    write_project_db(db)
    update_perms(db)
    os.chown(project_db_path(args.project), os.getuid(), os.getgid())

def delete_project(args):
    check_project_exists(args.project)

    db = read_project_db(args.project)
    if db.owner != args.executer:
        fail("Only the project owner can delete a project")

    for path in project_dirs(args.project).values():
        shutil.rmtree(path)
    os.remove(project_db_path(args.project))

def print_info(args):
    check_project_exists(args.project)
    db = read_project_db(args.project)
    print(db)

def refresh_permissions(args):
    check_project_exists(args.project)
    db = read_project_db(args.project)

    if (args.executer not in db.members and args.executer not in db.collaborators
            and args.executer != db.owner):
        fail("Only a project member may refresh the project's permissions")

    update_perms(db)

def update_perms(db):
    # Yuck, specifying individual project directories here
    dirs = project_dirs(db.project)
    datadir = dirs["data"]
    set_access(datadir, db.owner, db.members + db.collaborators, [], db.public)
    archivedir = dirs["archive"]
    set_access(archivedir, db.owner, db.members, db.collaborators, db.public)

    set_access(project_db_path(db.project), db.owner, [], [], db.public)

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

    db = read_project_db(args.project)

    if args.executer != db.owner and args.executer not in db.members:
        fail("Only a project owner/member can add/modify users")

    if args.username == db.owner:
        if args.role != "owner":
            fail("Can't remove permissions from owner. Set a new owner first")
        else:
            fail("Already project owner")
    if args.username in db.members:
        if args.role != MEMBER_ROLE:
            db.members.remove(args.username)
        else:
            fail("Already a member")
    if args.username in db.collaborators:
        if args.role != COLLAB_ROLE:
            db.collaborators.remove(args.username)
        else:
            fail("Already a collaborator")

    if args.role == "owner":
        db.owner = args.username
    elif args.role == MEMBER_ROLE:
        db.members.append(args.username)
    elif args.role == COLLAB_ROLE:
        db.collaborators.append(args.username)

    write_project_db(db)
    update_perms(db)

def del_user(args):
    check_project_exists(args.project)

    try:
        pwd.getpwnam(args.username)
    except KeyError:
        fail("User %s is not a valid user" % args.username)

    db = read_project_db(args.project)

    if args.executer != db.owner and args.executer not in db.members:
        fail("Only a project owner/member can delete users")

    if args.username == db.owner:
        fail("Can't delete owner. Set a new owner first")
    if args.username in db.members:
        db.members.remove(args.username)
    if args.username in db.collaborators:
        db.collaborators.remove(args.username)

    write_project_db(db)
    update_perms(db)

def check_project_exists(project):
    for path in project_dirs(project).values():
        if not os.path.isdir(path):
            fail("Project directory '%s' does not exist" % path)
    if not os.path.isfile(project_db_path(project)):
        fail("Project user database does not exist")

def project_dirs(project_name):
    """
    Create a dict containing paths to each relevant project directory.
    Currently: data, archive.
    """
    dirs = {}
    for name in ["data", "archive"]:
        dirs[name] = os.path.join(PROJECT_ROOT, name, project_name)
    return dirs

def project_db_path(project_name):
    """Dynamically forms a project's user database path
    Modify this function if you change the location of a project's DB.
    """
    return os.path.join(PROJECT_ROOT, "config", "%s.yml" % project_name)

def write_project_db(db):
    """Writes a project YAML file to disk."""
    stuff = {
            "public":db.public,
            "owner":db.owner,
            "members":db.members,
            "collaborators":db.collaborators}
    with open(project_db_path(db.project), 'w') as fobj:
        fobj.write(yaml.dump(stuff, default_flow_style=False))

def read_project_db(project_name):
    """ Reads a project YAML file and returns the a ProjectDB instance."""
    with open(project_db_path(project_name)) as fobj:
        loaded = yaml.load(fobj.read())
    db = ProjectDB(project_name, loaded["owner"],
            loaded["public"], loaded["members"], loaded["collaborators"])
    return db


if __name__ == "__main__":
    main()
