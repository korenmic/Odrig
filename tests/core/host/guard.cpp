// Replaces the global allocation functions of C++ so that every `new` of the program goes
// through the guard. With the flag raised, an allocation ends the program.

#include "guard.h"

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <new>

#ifdef _WIN32
#include <malloc.h>
#endif

namespace guard {

bool raised = false;

void stop() {
    std::fputs("allocation after startup\n", stdout);
    std::fflush(stdout);
    std::_Exit(kAllocationAfterStartup);
}

}  // namespace guard

namespace {

// Whether a block of this alignment comes from `malloc`, which aligns for every ordinary
// object, or from the call of the system for a wider alignment.
bool ordinary(std::size_t alignment) { return alignment <= alignof(std::max_align_t); }

void *allocate(std::size_t size, std::size_t alignment) {
    if (guard::raised) {
        guard::stop();
    }
    void *block = nullptr;
    if (ordinary(alignment)) {
        block = std::malloc(size != 0 ? size : 1);
    } else {
#ifdef _WIN32
        block = _aligned_malloc(size != 0 ? size : 1, alignment);
#else
        if (posix_memalign(&block, alignment, size != 0 ? size : 1) != 0) {
            block = nullptr;
        }
#endif
    }
    if (block == nullptr) {
        std::abort();
    }
    return block;
}

// Gives back a block that `allocate` gave for this alignment. On Windows a block with a
// wider alignment has a call of its own for that.
void release(void *block, std::size_t alignment) {
#ifdef _WIN32
    if (!ordinary(alignment)) {
        _aligned_free(block);
        return;
    }
#else
    (void)alignment;
#endif
    std::free(block);
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
void operator delete(void *block, std::align_val_t alignment) noexcept { release(block, static_cast<std::size_t>(alignment)); }
void operator delete[](void *block, std::align_val_t alignment) noexcept { release(block, static_cast<std::size_t>(alignment)); }
void operator delete(void *block, std::size_t, std::align_val_t alignment) noexcept { release(block, static_cast<std::size_t>(alignment)); }
void operator delete[](void *block, std::size_t, std::align_val_t alignment) noexcept { release(block, static_cast<std::size_t>(alignment)); }
void operator delete(void *block, std::align_val_t alignment, const std::nothrow_t &) noexcept { release(block, static_cast<std::size_t>(alignment)); }
void operator delete[](void *block, std::align_val_t alignment, const std::nothrow_t &) noexcept { release(block, static_cast<std::size_t>(alignment)); }
