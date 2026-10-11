// The benchmark of the core's ODRG decoder: how long one frame record takes to decode.
//
//   odrig_bench FILE...
//
// Each file is held in memory and decoded ten times from its first record to its last.
// The time of every decoded record is taken. Nothing here passes or fails on a time.

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "file_source.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "odrig_core.h"
#include "reasons.h"

namespace {

const int kPasses = 10;

// One file in memory, handed out in pieces of the size the core asks for.
struct Memory {
    std::string bytes;
    size_t offset = 0;
};

int open_file(void *ctx, const char *) {
    static_cast<Memory *>(ctx)->offset = 0;
    return 1;
}

int32_t read_file(void *ctx, uint8_t *buffer, size_t capacity) {
    Memory &memory = *static_cast<Memory *>(ctx);
    size_t count = memory.bytes.size() - memory.offset;
    if (count > capacity) {
        count = capacity;
    }
    std::memcpy(buffer, memory.bytes.data() + memory.offset, count);
    memory.offset += count;
    return static_cast<int32_t>(count);
}

void close_file(void *) {}

bool load(const char *path, std::string *bytes) {
    std::FILE *file = std::fopen(path, "rb");
    if (file == nullptr) {
        return false;
    }
    char buffer[65536];
    size_t count;
    while ((count = std::fread(buffer, 1, sizeof buffer, file)) > 0) {
        bytes->append(buffer, count);
    }
    bool failed = std::ferror(file) != 0;
    std::fclose(file);
    return !failed;
}

// Decodes the file kPasses times and prints its row. False when the file is refused.
bool measure(const char *path) {
    Memory memory;
    if (!load(path, &memory.bytes)) {
        std::fprintf(stderr, "odrig_bench: %s cannot be read\n", path);
        return false;
    }
    odrig_host host;
    std::memset(&host, 0, sizeof host);
    host.ctx = &memory;
    host.open = open_file;
    host.read = read_file;
    host.close = close_file;

    odrig::FileSource file;
    std::memset(&file, 0, sizeof file);
    odrig::Inflate inflate;
    std::memset(&inflate, 0, sizeof inflate);
    odrig::OdrgDecoder decoder;
    std::memset(&decoder, 0, sizeof decoder);
    std::vector<uint8_t> window(odrig::kWindowSize);
    std::vector<uint8_t> pixels;

    double total_us = 0;
    double longest_us = 0;
    uint64_t records = 0;
    uint32_t frames = 0;
    for (int pass = 0; pass < kPasses; ++pass) {
        odrig::Reason reason = file.open(host, path);
        if (reason == odrig::kNone) {
            reason = decoder.open(&file, &inflate, window.data());
        }
        if (reason == odrig::kNone) {
            frames = decoder.frames;
            pixels.assign(decoder.n, 0);
        }
        for (uint32_t record = 0; reason == odrig::kNone && record < decoder.frames; ++record) {
            uint16_t duration = 0;
            auto before = std::chrono::steady_clock::now();
            reason = decoder.next(pixels.data(), &duration);
            auto after = std::chrono::steady_clock::now();
            double us = std::chrono::duration<double, std::micro>(after - before).count();
            total_us += us;
            if (us > longest_us) {
                longest_us = us;
            }
            ++records;
        }
        if (reason == odrig::kNone) {
            reason = decoder.finish();
        }
        file.close();
        if (reason != odrig::kNone) {
            std::fprintf(stderr, "odrig_bench: %s is refused: %s\n", path, odrig::reason_name(reason));
            return false;
        }
    }

    const char *name = std::strrchr(path, '/');
    name = name != nullptr ? name + 1 : path;
    std::printf("%-22s %7zu %7u %8.1f %7.1f\n", name, memory.bytes.size(), frames, total_us / static_cast<double>(records),
                longest_us);
    return true;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc < 2) {
        std::fputs("usage: odrig_bench FILE...\n", stderr);
        return 64;
    }
    std::printf("%-22s %7s %7s %8s %7s\n", "file", "bytes", "frames", "mean_us", "max_us");
    for (int index = 1; index < argc; ++index) {
        if (!measure(argv[index])) {
            return 1;
        }
    }
    return 0;
}
