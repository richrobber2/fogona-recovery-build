// SPDX-License-Identifier: Apache-2.0
// Restricted front end to the pinned recovery libresetprop already in use.
#include <cstring>
#include <sys/stat.h>
#include <unistd.h>
int resetprop_main(int, char**);
void cmdline_logging();
int main(int argc, char** argv) {
    if (geteuid() != 0 || argc != 4 || std::strcmp(argv[1], "-n") ||
        (std::strcmp(argv[2], "ro.build.version.release") &&
         std::strcmp(argv[2], "ro.build.version.security_patch"))) return 2;
    umask(077);
    cmdline_logging();
    return resetprop_main(argc, argv);
}
