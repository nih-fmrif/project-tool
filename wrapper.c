#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

const char script[] = "/usr/local/lib/project-manager.py";

int main(int argc, char** argv)
{
    uid_t uid = getuid();
    uid_t euid = geteuid();

    if (euid != 0) {
        fprintf(stderr, "Warning: not running with root privileges");
    }

    /* copy argument array and NULL terminate the argument array */
    char **args = malloc((argc + 1) * sizeof(*args));
    if (args == NULL) {
        fprintf(stderr, "malloc error, uh oh\n");
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
        fprintf(stderr, "execvp error\n");
        return EXIT_FAILURE;
    }

    /* you'll never get here */
    return EXIT_SUCCESS;
}
