import argparse

def main():
    parser = argparse.ArgumentParser(
            prog="project",
            description="Manage projects",
            epilog="See `man project` for more details",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-P", "--project-root", metavar="<root>",
            help="project root directory")
    parser.set_defaults(project_root="SJKDFLAKSJDF",)

    subparsers = parser.add_subparsers(title="commands", dest="which",
            metavar="<command>")

    parent_parser = argparse.ArgumentParser(add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parent_parser.add_argument("project", help="name of project")

    list_parser = subparsers.add_parser("list",
            help="list all projects",
            epilog="List all projects found in PROJECT_ROOT",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    list_parser.set_defaults(func=None)

    create_parser = subparsers.add_parser("create",
            help="create new project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    create_parser.add_argument("--public", action="store_true",
            help="make project publicly readable")
    create_parser.set_defaults(func=None)

    delete_parser = subparsers.add_parser("delete",
            help="delete existing project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    delete_parser.set_defaults(func=None)

    info_parser = subparsers.add_parser("info",
            help="print information about project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    info_parser.set_defaults(func=None)

    refresh_parser = subparsers.add_parser("refresh",
            help="refresh permissions on project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    refresh_parser.set_defaults(func=None)

    user_parser = argparse.ArgumentParser(add_help=False,
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    user_parser.add_argument("username", help="user's UNIX username")
    user_parser.add_argument("role", choices=["cool", "dumb"],
            #metavar="role",
            help="new user role")

    add_user_parser = subparsers.add_parser("adduser",
            help="add user to project",
            parents=[user_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    add_user_parser.set_defaults(func=None)

    mod_user_parser = subparsers.add_parser("moduser",
            help="modify user permissions",
            parents=[user_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    mod_user_parser.set_defaults(func=None)

    del_user_parser = subparsers.add_parser("deluser",
            help="remove user from project",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    del_user_parser.add_argument("username", help="user's UNIX username")
    del_user_parser.set_defaults(func=None)

    help_parser = subparsers.add_parser('help',
            help="print help info for command",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    help_parser.add_argument("command", help="project command")

    args = parser.parse_args()

    if args.which == 'help':
        subp = subparsers.choices[args.command]
        subp.print_help()

main()
