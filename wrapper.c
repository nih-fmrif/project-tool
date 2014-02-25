#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>

const char script[] = "/usr/local/lib/project_manager.py";

int main(int argc, char** argv)
{
    uid_t uid = getuid();
    uid_t euid = geteuid();

    if (euid != 0) {
        fprintf(stderr, "WARNING: not running with superuser privileges\n");
    }

    /* copy argument array and NULL terminate the argument array */
    char **args = malloc((argc + 1) * sizeof(*args));
    if (args == NULL) {
        fprintf(stderr, "Error: Failed to allocate memory\n");
        return EXIT_FAILURE;
    }

    args[0] = (char *)script;

    int i;
    for (i = 1; i < argc; i++) {
        /* copy all arguments */
        args[i] = argv[i];
    }
    args[argc] = NULL;  /* NULL terminate the array of args */

    int ret = execvp(args[0], args);
    if (ret == -1) {
        const char * msg;
        switch (errno) {
            case ENOENT:
                msg = "Could not find project_manager.py.";
                break;
            default:
                msg = strerror(errno);
        }
        fprintf(stderr, "ERROR: %s\n", msg);
        return EXIT_FAILURE;
    }

    /* you'll never get here */
    return EXIT_SUCCESS;
}
