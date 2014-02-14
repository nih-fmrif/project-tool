% PANDOC(1) FMRIF User Manuals
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

create [*--public*] *PROJECT-NAME*
:   Create new project. By default, projects are made 'private',
    i.e. they are NOT world-readable.

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

adduser *PROJECT-NAME* *USERNAME* *ROLE*
:   Add user to project, where *USERNAME* must be a valid
    username on the system, and role is one of:
        owner, member, collaborator

moduser *PROJECT-NAME* *USERNAME* *ROLE*
:   Modify user permissions, where *USERNAME* must be a valid
    username on the system, and role is one of:
        owner, member, collaborator

deluser *PROJECT-NAME* *USERNAME*
:   Remove user from project.

help *COMMAND*
:   Print help info for command

# Environment
**PROJECT_ROOT** - Parent directory of projects (defaults to */fmrif/projects*)

# Examples

1.  Create a project

        project create demo

    use the *--public* flag to make the project world-readable.

1.  List available projects

        project list

1. Add a user to a project

      project adduser demo john member
      project adduser demo mary collaborator

1. Change a user's role

      project moduser demo john collaborator

1. Remove a user from a project

      project deluser demo mary

1. Print information about a project

      project info demo

1. Fix permissions for a project

      project update demo

1. Delete a project (use **very** carefully)

      project delete demo

# Bugs
This tool is **setuid**. Run with caution.

# See Also
`chown(1)`, `getfacl(1)`, `setfacl(1)`
