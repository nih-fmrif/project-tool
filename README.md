# UNIX Project Management

## Dependencies

PyLibACL: https://github.com/iustin/pylibacl

## Build

Type `make` to build a binary that calls the Python program as well as a manpage.

`make install` will install the binary in `/usr/local/bin`, the python program in
`/usr/local/lib` and the manpage in `/usr/local/share/man/man1`)

## Test

Run the few existing tests: `make test` or `nosetests`

## Security Issues

The setuid binary tool (owned by root) simply executes the Python script.
Any dangerous code in the Python script will be executed with superuser permissions.

### Example:

Let's say I have a directory called `code/` in my `$HOME` directory.

- I have no "projects" anywhere in my home directory

    ```bash
    [naegelejd@erbium acls]$ project -P $HOME list
    [naegelejd@erbium acls]$ project -P $HOME info code
    Project config '/users/naegelejd/.code.yml' does not exist
    ```

- The project tool can create projects anywhere

    ```bash
    [naegelejd@erbium acls]$ project -P $HOME code2
    [naegelejd@erbium acls]$ project -P $HOME list
    code2
    [naegelejd@erbium acls]$ project -P $HOME info code2
    Owner: naegelejd
    Members:
    Collaborators:
    Public: False
    ```

- A project is just a directory, config file, and a Posix Access Control List

    ```bash
    [naegelejd@erbium acls]$ project -P $HOME info code2
    [naegelejd@erbium acls]$ project -P $HOME info code
    Owner: naegelejd
    Members:
    Collaborators:
    Public: False
    ```

- Projects can be deleted

    ```bash
    [naegelejd@erbium acls]$ project -P $HOME delete code
    [naegelejd@erbium acls]$ ls $HOME/code
    ls: cannot access /users/naegelejd/code: No such file or directory
    ```

I just deleted all my code!
