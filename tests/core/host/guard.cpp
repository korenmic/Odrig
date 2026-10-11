// Replaces the global allocation functions of C++ so that every `new` of the program goes
// through the guard. With the flag raised, an allocation ends the program.

#include "guard.h"

#include <cstdio>
#include <cstdlib>
#include <new>

namespace guard {

bool raised = false;

void stop() {
    std::fputs("allocation after startup\n", stdout);
    std::fflush(stdout);
    std::_Exit(kAllocationAfterStartup);
}

}  // namespace guard

namespace {

void *allocate(std::size_t size, std::size_t alignment) {
    if (guard::raised) {
        guard::stop();
    }
    void *block = nullptr;
    if (alignment <= alignof(std::max_align_t)) {
        block = std::malloc(size != 0 ? size : 1);
    } else if (posix_memalign(&block, alignment, size != 0 ? size : 1) != 0) {
        block = nullptr;
    }
    if (block == nullptr) {
        std::abort();
    }
    return block;
}

}  // namespace

void *operator new(std::size_t size) { return allocate(size, 1); }
void *operator new[](std::size_t size) { return allocate(size, 1); }
void *operator new(std::size_t size, const std::nothrow_t &) noexcept { return allocate(size, 1); }
void *operator new[](std::size_t size, const std::nothrow_t &) noexcept { return allocate(size, 1); }
void *operator new(std::size_t size, std::align_val_t alignment) {
    return allocate(size, static_cast<std::size_t>(alignment));
}
void *operator new[](std::size_t size, std::align_val_t alignment) {
    return allocate(size, static_cast<std::size_t>(alignment));
}
void *operator new(std::size_t size, std::align_val_t alignment, const std::nothrow_t &) noexcept {
    return allocate(size, static_cast<std::size_t>(alignment));
}
void *operator new[](std::size_t size, std::align_val_t alignment, const std::nothrow_t &) noexcept {
    return allocate(size, static_cast<std::size_t>(alignment));
}

void operator delete(void *block) noexcept { std::free(block); }
void operator delete[](void *block) noexcept { std::free(block); }
void operator delete(void *block, std::size_t) noexcept { std::free(block); }
void operator delete[](void *block, std::size_t) noexcept { std::free(block); }
void operator delete(void *block, const std::nothrow_t &) noexcept { std::free(block); }
void operator delete[](void *block, const std::nothrow_t &) noexcept { std::free(block); }
void operator delete(void *block, std::align_val_t) noexcept { std::free(block); }
void operator delete[](void *block, std::align_val_t) noexcept { std::free(block); }
void operator delete(void *block, std::size_t, std::align_val_t) noexcept { std::free(block); }
void operator delete[](void *block, std::size_t, std::align_val_t) noexcept { std::free(block); }
void operator delete(void *block, std::align_val_t, const std::nothrow_t &) noexcept { std::free(block); }
void operator delete[](void *block, std::align_val_t, const std::nothrow_t &) noexcept { std::free(block); }
