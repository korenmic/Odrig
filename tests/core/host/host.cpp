// The test host: a program around the core that the suite of tests/core drives as a child
// process. It has no clock; whatever it prints depends on its arguments and its input only.

#include <cstdio>
#include <cstring>

#include "reasons.h"

namespace {

const int kUsage = 64;

int usage() {
    std::fputs("usage: odrig_host reasons\n", stderr);
    return kUsage;
}

// Prints every name reason_name can return, one per line.
int reasons() {
    for (int value = 0; value < odrig::kReasonCount; ++value) {
        const char *name = odrig::reason_name(static_cast<odrig::Reason>(value));
        if (name[0] != '\0') {
            std::printf("%s\n", name);
        }
    }
    return 0;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc == 2 && std::strcmp(argv[1], "reasons") == 0) {
        return reasons();
    }
    return usage();
}
