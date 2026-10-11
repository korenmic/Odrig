// The test host: a program around the core that the suite of tests/core drives as a child
// process. It has no clock; whatever it prints depends on its arguments and its input only.

#include <sys/stat.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "file_source.h"
#include "inflate.h"
#include "odrig_core.h"
#include "reasons.h"

namespace {

const int kUsage = 64;
const int kFileMisuse = 71;

int usage() {
    std::fputs(
        "usage: odrig_host reasons\n"
        "       odrig_host inflate [--batch]\n",
        stderr);
    return kUsage;
}

// Prints one line and ends the program at once with the given status.
[[noreturn]] void stop(const char *line, int status) {
    std::printf("%s\n", line);
    std::fflush(stdout);
    std::_Exit(status);
}

std::string hex(const std::string &bytes) {
    static const char digits[] = "0123456789abcdef";
    std::string text;
    text.reserve(2 * bytes.size());
    for (unsigned char byte : bytes) {
        text += digits[byte >> 4];
        text += digits[byte & 15];
    }
    return text;
}

std::string standard_input() {
    std::string bytes;
    char buffer[65536];
    size_t count;
    while ((count = std::fread(buffer, 1, sizeof buffer, stdin)) > 0) {
        bytes.append(buffer, count);
    }
    return bytes;
}

// The pieces of a batch: each piece follows its length, four bytes, least significant first.
std::vector<std::string> batch(const std::string &bytes) {
    std::vector<std::string> pieces;
    size_t at = 0;
    while (at < bytes.size()) {
        if (bytes.size() - at < 4) {
            stop("bad batch", kUsage);
        }
        size_t length = 0;
        for (int i = 3; i >= 0; --i) {
            length = (length << 8) | static_cast<unsigned char>(bytes[at + i]);
        }
        at += 4;
        if (bytes.size() - at < length) {
            stop("bad batch", kUsage);
        }
        pieces.push_back(bytes.substr(at, length));
        at += length;
    }
    return pieces;
}

// The files the core may ask for: those of a folder on disk, or one text held in memory
// that every name opens. It also checks how the core uses the three file functions.
class Files {
public:
    static Files of_folder(const std::string &folder) {
        Files files;
        files.folder_ = folder;
        return files;
    }

    static Files of_memory(const std::string &bytes) {
        Files files;
        files.in_memory_ = true;
        files.memory_ = bytes;
        return files;
    }

    // The host interface over these files. The object must stay where it is while in use.
    odrig_host host() {
        odrig_host functions;
        std::memset(&functions, 0, sizeof functions);
        functions.ctx = this;
        functions.open = open;
        functions.read = read;
        functions.close = close;
        return functions;
    }

private:
    // A real file system may give fewer bytes than asked for. The reads of a file take these
    // sizes in turn, so the core is run against short reads in every test.
    static constexpr size_t kReadSizes[] = {512, 1, 7, 512, 100, 512, 3, 255};

    static int open(void *ctx, const char *name) {
        Files &files = *static_cast<Files *>(ctx);
        if (files.is_open_) {
            stop("file misuse", kFileMisuse);
        }
        if (files.in_memory_) {
            files.content_ = files.memory_;
        } else {
            int found = files.load(name);
            if (found != 1) {
                return found;
            }
        }
        files.is_open_ = true;
        files.offset_ = 0;
        files.reads_ = 0;
        return 1;
    }

    static int32_t read(void *ctx, uint8_t *buffer, size_t capacity) {
        Files &files = *static_cast<Files *>(ctx);
        if (!files.is_open_ || capacity == 0 || capacity > 512) {
            stop("file misuse", kFileMisuse);
        }
        size_t count = kReadSizes[files.reads_++ % (sizeof kReadSizes / sizeof kReadSizes[0])];
        count = std::min(count, capacity);
        count = std::min(count, files.content_.size() - files.offset_);
        std::memcpy(buffer, files.content_.data() + files.offset_, count);
        files.offset_ += count;
        return static_cast<int32_t>(count);
    }

    static void close(void *ctx) {
        Files &files = *static_cast<Files *>(ctx);
        if (!files.is_open_) {
            stop("file misuse", kFileMisuse);
        }
        files.is_open_ = false;
    }

    // Loads a file of the folder: 1 when loaded, 0 when there is no such file, -1 otherwise.
    int load(const char *name) {
        if (std::strchr(name, '/') != nullptr) {
            return -1;
        }
        std::string path = folder_ + "/" + name;
        struct stat status;
        if (stat(path.c_str(), &status) != 0) {
            return 0;
        }
        if (!S_ISREG(status.st_mode)) {
            return -1;
        }
        std::FILE *file = std::fopen(path.c_str(), "rb");
        if (file == nullptr) {
            return -1;
        }
        content_.clear();
        char buffer[65536];
        size_t count;
        while ((count = std::fread(buffer, 1, sizeof buffer, file)) > 0) {
            content_.append(buffer, count);
        }
        bool failed = std::ferror(file) != 0;
        std::fclose(file);
        return failed ? -1 : 1;
    }

    std::string folder_;
    bool in_memory_ = false;
    std::string memory_;
    std::string content_;
    bool is_open_ = false;
    size_t offset_ = 0;
    size_t reads_ = 0;
};

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

// Decodes one raw DEFLATE stream with the core's decoder. Prints `data <hex>` and
// `left <bytes of input after the stream>`, or `rejected <reason>`.
void inflate_one(const std::string &stream) {
    Files files = Files::of_memory(stream);
    odrig_host host = files.host();
    odrig::FileSource file;
    std::memset(&file, 0, sizeof file);
    odrig::Inflate inflate;
    std::memset(&inflate, 0, sizeof inflate);
    std::vector<uint8_t> window(odrig::kWindowSize);

    if (file.open(host, "stream") != odrig::kNone) {
        stop("the stream did not open", 1);
    }
    inflate.start(&file, window.data());
    std::string output;
    int got;
    while ((got = inflate.get()) >= 0) {
        output += static_cast<char>(got);
    }
    if (inflate.get() != got || inflate.get() != got) {
        stop("the decoder changed its answer", 1);
    }
    if (got == -odrig::kEnd) {
        size_t left = 0;
        while (file.get() >= 0) {
            ++left;
        }
        std::printf("data %s\nleft %zu\n", hex(output).c_str(), left);
    } else {
        std::printf("rejected %s\n", odrig::reason_name(static_cast<odrig::Reason>(-got)));
    }
    file.close();
}

int inflate(bool in_batch) {
    std::string input = standard_input();
    if (!in_batch) {
        inflate_one(input);
        return 0;
    }
    for (const std::string &stream : batch(input)) {
        inflate_one(stream);
    }
    return 0;
}

}  // namespace

int main(int argc, char **argv) {
    std::vector<std::string> arguments(argv + 1, argv + argc);
    if (arguments.size() == 1 && arguments[0] == "reasons") {
        return reasons();
    }
    if (!arguments.empty() && arguments[0] == "inflate") {
        if (arguments.size() == 1) {
            return inflate(false);
        }
        if (arguments.size() == 2 && arguments[1] == "--batch") {
            return inflate(true);
        }
    }
    return usage();
}
