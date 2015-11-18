#compdef project
#autoload

# Rename or link this file to _project somewhere on your $fpath (e.g. /usr/share/zsh/site-functions)

_project_all_projects() {
    all_projects=(`project list --all`)
}

_project_my_projects() {
    my_projects=(`project list`)
}

_project_roles() {
    roles="owner member collaborator"
}

_project_users() {
    users=(`project info "$1" 2>/dev/null | egrep '^[[:space::]+' | sed 's/\s//g'`)
}

local -a _project_commands
_project_commands=(
    'create:create new project'
    'rename:rename project'
    'delete:delete existing project'
    'info:print information about project'
    'update:update permissions on project'
    'adduser:add user to project'
    'moduser:modify user permissions'
    'deluser:remove user from project'
    'list:list projects'
    'check:check project permissions'
    'help:print help info for command'
)

local -a my_projects all_projects users roles

_project() {
    _arguments -s \
        {-h,--help}'[show help]' \
        {-P,--project-root}'[project-root dir]:DIR:_files -/' \
        {-v,--verbose}'[verbose mode]' \
        {-d,--debug}'[debug mode]' \
        --nocolor'[disable color]' \
        '*::project commands:_project_command' \
        && return 0
}

_project_command() {
    local expl
    local -a _project_commands
    _project_cmds=(
        'create:create new project'
        'rename:rename project'
        'delete:delete existing project'
        'info:print information about project'
        'update:update permissions on project'
        'adduser:add user to project'
        'moduser:modify user permissions'
        'deluser:remove user from project'
        'list:list projects'
        'check:check project permissions'
        'help:print help info for command'
    )

    if (( CURRENT == 1 )); then
        _describe -t commands "project subcommand" _project_cmds
        return
    else
        case "$words[1]" in
            info|update|rename|delete|adduser|moduser|deluser)
                _project_my_projects
                # _arguments -s \
                #     -x'[fake option]' \
                #     && return 0
                _wanted projects expl 'my projects' compadd -a my_projects
            ;;
        esac
    fi

    return 0
}

_project "$@"
