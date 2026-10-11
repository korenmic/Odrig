// The guard of the test host: it stops the program when memory is asked for while the core
// runs after startup.

#ifndef ODRIG_HOST_GUARD_H
#define ODRIG_HOST_GUARD_H

namespace guard {

const int kAllocationAfterStartup = 70;

// True while the program is inside a function of the core that it called after startup.
extern bool raised;

// Prints `allocation after startup` and ends the program with status 70.
[[noreturn]] void stop();

// Raises the flag for the length of one call into the core.
struct InCore {
    InCore() { raised = true; }
    ~InCore() { raised = false; }
};

// Lowers the flag while a function of the host runs that the core has called: the host may
// use memory of its own.
struct InHost {
    InHost() : was(raised) { raised = false; }
    ~InHost() { raised = was; }
    bool was;
};

}  // namespace guard

#endif
