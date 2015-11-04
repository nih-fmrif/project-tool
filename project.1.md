% PROJECT(1) FMRIF User Manuals
% Joseph Naegele <naegelejd@mail.nih.gov>
% February 2014

# NAME
**project** - Manage shared directories

# Synopsis
**project** command *project-name* [...]

# Description
The project tool allows users to create and maintain shared directories.
Project directories can be made public or private only to members/collaborators.
There are three roles for users of a project:

- Owner: The project creator
- Member: Users who can read and write in the project directory
- Collaborator: Users who can only read files in the project directory

Each project has a corresponding YAML file (*PROJECT_ROOT/.projectname.yml*) which stores
configuration information about the project. This file can be modified manually
if necessary, but you will afterwards need to run an **update** on the project.

The project tool uses POSIX ACLs under the hood, so you can modify/inspect the permissions
on your files manually using **setfacl**/**getfacl**, respectively.

# Options

-p <root>, --project-root <root>
:   manually specify a parent directory for a project *command*

## Commands

list
:   list all projects

check
:   check that all project permissions are correct. This checks
    every file in each project so it may take a while.

create [*--public*] *PROJECT-NAME*
:   Create new project. By default, projects are made 'private',
    i.e. they are NOT world-readable.

rename *PROJECT-NAME* *NEW-NAME*
:   Rename/Move a project within *PROJECT_ROOT*.

delete *PROJECT-NAME*
:   Delete existing project.
    There is no un-delete option, so use this command
    **very** carefully.

info *PROJECT-NAME*
:   Print information about project

update *PROJECT-NAME*
:   Update permissions on project.
    This is especially useful if someone manually changes
    some file permissions, or if a project's configuration
    file is manually modified.

adduser *PROJECT-NAME* *ROLE* *USERNAME*...
:   Add user to project, where *USERNAME* must be a valid
    username on the system, and role is one of:
        owner, member, collaborator

moduser *PROJECT-NAME* *ROLE* *USERNAME*...
:   Modify user permissions, where *USERNAME* must be a valid
    username on the system, and role is one of:
        owner, member, collaborator

deluser *PROJECT-NAME* *USERNAME*...
:   Remove user from project.

help [*COMMAND*]
:   Print help info for command

# Environment

**PROJECT_ROOT** - Parent directory of projects (defaults to */fmrif/projects*)

# Examples

Create a project:

    project create demo

use the *--public* flag to make the project world-readable.

List available projects:

    project list

Add a user to a project:

    project adduser demo-project member john mary
    project adduser demo-project collaborator jack

Change a user's role:

    project moduser demo-project collaborator john

Remove a user from a project:

    project deluser demo-project mary

Print information about a project:

    project info demo-project

Fix permissions for a project:

    project update demo-project

Fix permissions for all projects having broken permissions:

    project check | xargs -n 1 project update

Delete a project (use **very** carefully):

    project delete demo-project

# Bugs

- Project config files are created with rwx (0770) permissions.
  The should be created with rw- (0660) permissions.

# Security Issues

This tool has its setuid bit set and is owned by root
(like ``top``, ``ps``, ``traceroute``, etc.). This allows the tool
to effectively run as root, even when a regular user executes it.
This, in general, is dangerous if not handled correctly. The tool is
designed to not run arbitrary code, however it is capable of deleting
any directory if a *valid* configuration file can be found.

# See Also
`chown(1)`, `getfacl(1)`, `setfacl(1)`
