# adapted from Homebrew brew_bash_completion.sh
# Copyright 2009-2015 Homebrew contributors.
# See LICENSE file

__projectcomp_words_include ()
{
    local i=1
    while [[ $i -lt $COMP_CWORD ]]; do
        if [[ "${COMP_WORDS[i]}" = "$1" ]]; then
            return 0
        fi
        i=$((++i))
    done
    return 1
}

# Find the previous non-switch word
__projectcomp_prev ()
{
    local idx=$((COMP_CWORD - 1))
    local prv="${COMP_WORDS[idx]}"
    while [[ $prv == -* ]]; do
        idx=$((--idx))
        prv="${COMP_WORDS[idx]}"
    done
    echo "$prv"
}

__projectcomp_indexof ()
{
    local i=1
    while [[ $i -lt $COMP_CWORD ]]; do
        local s="${COMP_WORDS[i]}"
        case "$s" in
        "$1")
            break
            ;;
        esac
        i=$((++i))
    done
    echo "$i"
}

__projectcomp ()
{
    # break $1 on space, tab, and newline characters,
    # and turn it into a newline separated list of words
    local list s sep=$'\n' IFS=$' '$'\t'$'\n'
    local cur="${COMP_WORDS[COMP_CWORD]}"

    for s in $1; do
        __projectcomp_words_include "$s" && continue
        list="$list$s$sep"
    done

    IFS=$sep
    COMPREPLY=($(compgen -W "$list" -- "$cur"))
}

__project_complete_projects ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local root="/fmrif/projects"
    #local projects=$(find /fmrif/projects/ -maxdepth 1 -type f -name "*.yml" -printf '%f\n' | sed 's/\.\(.\+\)\.yml/\1/g')
    local projects=$(project list --all)

    COMPREPLY=($(compgen -W "$projects" -- "$cur"))
}

__project_complete_roles ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -W "collaborator member owner" -- "$cur"))
}

__project_complete_usernames ()
{
    local idx=$1
    local proj="${COMP_WORDS[idx]}"
    local users=$(project info "${proj}" 2>/dev/null | egrep '^[[:space:]]+' | sed 's/\s//g')
    COMPREPLY=($(compgen -W "$users" -- "$cur"))
}

_project_create ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help --public"
        return
        ;;
    esac
}

_project_rename ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac
    __project_complete_projects
}

_project_delete ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac
    __project_complete_projects
}

_project_info ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h"
        return
        ;;
    esac
    __project_complete_projects
}

_project_update ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac
    __project_complete_projects
}

_project_adduser ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac

    local i=$(__projectcomp_indexof adduser)

    if [ "${COMP_CWORD}" -eq $((i+1)) ]; then
        __project_complete_projects
    elif [ "${COMP_CWORD}" -eq $((i+2)) ]; then
        __project_complete_roles
    fi
}

_project_moduser ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac

    local i=$(__projectcomp_indexof moduser)

    if [ "${COMP_CWORD}" -eq $((i+1)) ]; then
        __project_complete_projects
    elif [ "${COMP_CWORD}" -eq $((i+2)) ]; then
        __project_complete_roles
    elif [ "${COMP_CWORD}" -eq $((i+3)) ]; then
        __project_complete_usernames $((i+1))
    fi
}

_project_deluser ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac

    local i=$(__projectcomp_indexof deluser)

    if [ "${COMP_CWORD}" -eq $((i+1)) ]; then
        __project_complete_projects
    elif [ "${COMP_CWORD}" -eq $((i+2)) ]; then
        __project_complete_usernames $((i+1))
    fi
}

_project_list ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help -a --all"
        return
        ;;
    esac
}

_project_check ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help -a --all"
        return
        ;;
    esac
}

_project_help ()
{
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "$cur" in
    -*)
        __projectcomp "-h --help"
        return
        ;;
    esac
}

_project ()
{
    local i=1 cmd

    # find the subcommand
    while [[ $i -lt $COMP_CWORD ]]; do
        local s="${COMP_WORDS[i]}"
        case "$s" in
        -*) ;;
        *)
            cmd="$s"
            break
            ;;
        esac
        i=$((++i))
    done

    if [[ $i -eq $COMP_CWORD ]]; then
        case "${COMP_WORDS[i]}" in
        -*)
            __projectcomp "-h --help -P --project-root -v --verbose -d --debug --nocolor"
            ;;
        *)
            __projectcomp "create rename delete info update adduser moduser deluser list check help"
            ;;
        esac
        return
    fi

    # subcommands have their own completion functions
    case "$cmd" in
    create)                     _project_create ;;
    rename)                     _project_rename ;;
    delete)                     _project_delete ;;
    info)                       _project_info ;;
    update)                     _project_update ;;
    list)                       _project_list ;;
    adduser)                    _project_adduser ;;
    moduser)                    _project_moduser ;;
    deluser)                    _project_deluser ;;
    list)                       _project_list ;;
    check)                      _project_check ;;
    help)                       _project_help ;;
    *)                          ;;
    esac
}

complete -o bashdefault -o default -F _project project
