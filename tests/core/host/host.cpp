// The test host: a program around the core that the suite of tests/core drives as a child
// process. It has no clock; whatever it prints depends on its arguments and its input only.

#include <sys/stat.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "file_source.h"
#include "guard.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "odrig_core.h"
#include "reasons.h"

namespace {

const int kUsage = 64;
const int kFileMisuse = 71;

int usage() {
    std::fputs(
        "usage: odrig_host reasons\n"
        "       odrig_host inflate [--batch]\n"
        "       odrig_host decode FILE | --batch\n"
        "       odrig_host session DIR | --batch [--alloc-fails-at N] [--read-fails FILE OFFSET] [--trace-files]\n"
        "       odrig_host guard alloc | new\n",
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

// How a session differs from a plain one.
struct Options {
    long alloc_fails_at = 0;        // the number of the `alloc` call that returns NULL; 0 for none
    std::string read_fails_file;    // the file whose reading fails,
    long read_fails_offset = 0;     // and the offset at which `read` returns -1
    bool trace_files = false;       // print `open <name> <result>` for every `open`
};

// What the core is given: memory, files, and a place for its diagnostic text. The files are
// those of a folder on disk, or a set held in memory, or one text that every name opens. It checks how the core uses the file functions, and
// with the guard it stops the program when the core asks for memory after startup.
class Host {
public:
    static Host of_folder(const std::string &folder, const Options &options = Options()) {
        Host host;
        host.folder_ = folder;
        host.options_ = options;
        return host;
    }

    static Host of_files(const std::map<std::string, std::string> &files, const Options &options) {
        Host host;
        host.from_ = kFromFiles;
        host.files_ = files;
        host.options_ = options;
        return host;
    }

    static Host of_memory(const std::string &bytes) {
        Host host;
        host.from_ = kFromMemory;
        host.memory_ = bytes;
        return host;
    }

    Host(Host &&) = default;

    ~Host() {
        for (void *block : blocks_) {
            std::free(block);
        }
    }

    // The host interface. This object must stay where it is while the core uses it.
    odrig_host interface() {
        odrig_host functions;
        functions.ctx = this;
        functions.alloc = alloc;
        functions.open = open;
        functions.read = read;
        functions.close = close;
        functions.log = log;
        return functions;
    }

    size_t bytes_given() const { return bytes_given_; }
    size_t blocks_given() const { return blocks_.size(); }

private:
    Host() = default;

    // A real file system may give fewer bytes than asked for. The reads of a file take these
    // sizes in turn, so the core is run against short reads in every test.
    static constexpr size_t kReadSizes[] = {512, 1, 7, 512, 100, 512, 3, 255};

    static void *alloc(void *ctx, size_t bytes) {
        if (guard::raised) {
            guard::stop();
        }
        Host &host = *static_cast<Host *>(ctx);
        ++host.alloc_calls_;
        if (host.alloc_calls_ == host.options_.alloc_fails_at) {
            return nullptr;
        }
        void *block = std::calloc(1, bytes != 0 ? bytes : 1);
        if (block == nullptr) {
            std::abort();
        }
        host.blocks_.push_back(block);
        host.bytes_given_ += bytes;
        return block;
    }

    static int open(void *ctx, const char *name) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (host.is_open_) {
            stop("file misuse", kFileMisuse);
        }
        int found = 1;
        if (host.from_ == kFromMemory) {
            host.content_ = host.memory_;
        } else if (host.from_ == kFromFiles) {
            auto file = host.files_.find(name);
            found = file != host.files_.end() ? 1 : 0;
            if (found) {
                host.content_ = file->second;
            }
        } else {
            found = host.load(name);
        }
        if (host.options_.trace_files) {
            std::printf("open %s %d\n", name, found);
        }
        if (found != 1) {
            return found;
        }
        host.is_open_ = true;
        host.open_name_ = name;
        host.offset_ = 0;
        host.reads_ = 0;
        return 1;
    }

    static int32_t read(void *ctx, uint8_t *buffer, size_t capacity) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (!host.is_open_ || capacity == 0 || capacity > 512) {
            stop("file misuse", kFileMisuse);
        }
        size_t count = kReadSizes[host.reads_++ % (sizeof kReadSizes / sizeof kReadSizes[0])];
        count = std::min(count, capacity);
        count = std::min(count, host.content_.size() - host.offset_);
        if (host.open_name_ == host.options_.read_fails_file) {
            size_t fails_at = static_cast<size_t>(host.options_.read_fails_offset);
            if (host.offset_ >= fails_at) {
                return -1;
            }
            count = std::min(count, fails_at - host.offset_);
        }
        std::memcpy(buffer, host.content_.data() + host.offset_, count);
        host.offset_ += count;
        return static_cast<int32_t>(count);
    }

    static void close(void *ctx) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (!host.is_open_) {
            stop("file misuse", kFileMisuse);
        }
        host.is_open_ = false;
    }

    static void log(void *, const char *text) {
        guard::InHost lowered;
        std::printf("log %s\n", text);
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

    enum From { kFromFolder, kFromFiles, kFromMemory };

    Options options_;
    From from_ = kFromFolder;
    std::string folder_;
    std::map<std::string, std::string> files_;
    std::string memory_;

    std::string content_;
    std::string open_name_;
    bool is_open_ = false;
    size_t offset_ = 0;
    size_t reads_ = 0;

    long alloc_calls_ = 0;
    size_t bytes_given_ = 0;
    std::vector<void *> blocks_;
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
    Host host = Host::of_memory(stream);
    odrig_host functions = host.interface();
    odrig::FileSource file;
    std::memset(&file, 0, sizeof file);
    odrig::Inflate inflate;
    std::memset(&inflate, 0, sizeof inflate);
    std::vector<uint8_t> window(odrig::kWindowSize);

    if (file.open(functions, "stream") != odrig::kNone) {
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

// Reads one ODRG file with the core's decoder, as the core does when it checks a file.
// Prints `header <W> <H> <C> <F> <compressed>`, one `frame <ms> <hex>` for each record with
// the picture as three bytes for each pixel, then `end`; or, at the point where the file is
// refused, `rejected <reason>`.
void decode_one(Host &host, const char *name) {
    odrig_host functions = host.interface();
    odrig::FileSource file;
    std::memset(&file, 0, sizeof file);
    odrig::OdrgDecoder decoder;
    std::memset(&decoder, 0, sizeof decoder);
    odrig::Inflate inflate;
    std::memset(&inflate, 0, sizeof inflate);
    std::vector<uint8_t> window(odrig::kWindowSize);

    odrig::Reason reason = file.open(functions, name);
    if (reason == odrig::kNone) {
        reason = decoder.open(&file, &inflate, window.data());
    }
    if (reason == odrig::kNone) {
        std::printf("header %u %u %u %u %u\n", decoder.width, decoder.height, decoder.colours,
                    decoder.frames, decoder.compressed);
        std::vector<uint8_t> pixels(decoder.n, 0);
        std::string picture;
        for (uint32_t record = 0; record < decoder.frames && reason == odrig::kNone; ++record) {
            uint16_t duration = 0;
            reason = decoder.next(pixels.data(), &duration);
            if (reason != odrig::kNone) {
                break;
            }
            picture.clear();
            if (decoder.colours != 0) {
                for (uint8_t index : pixels) {
                    picture.append(reinterpret_cast<const char *>(decoder.palette) + 3 * index, 3);
                }
            } else {
                picture.assign(pixels.begin(), pixels.end());
            }
            std::printf("frame %u %s\n", duration, hex(picture).c_str());
        }
        if (reason == odrig::kNone) {
            reason = decoder.finish();
        }
    }
    file.close();
    if (reason == odrig::kNone) {
        std::printf("end\n");
    } else {
        std::printf("rejected %s\n", odrig::reason_name(reason));
    }
}

int decode(const std::string &argument) {
    if (argument == "--batch") {
        for (const std::string &content : batch(standard_input())) {
            Host host = Host::of_memory(content);
            decode_one(host, "file.odrg");
        }
        return 0;
    }
    size_t slash = argument.rfind('/');
    std::string folder = slash == std::string::npos ? "." : argument.substr(0, slash);
    std::string name = slash == std::string::npos ? argument : argument.substr(slash + 1);
    Host host = Host::of_folder(folder);
    decode_one(host, name.c_str());
    return 0;
}

// One core on a set of files, and the lines of a script given to it.
class Session {
public:
    explicit Session(Host &&host) : host_(std::move(host)) {}

    int run(std::istream &script) {
        odrig_host functions = host_.interface();
        core_ = odrig_core_begin(&functions);
        if (core_ == nullptr) {
            std::printf("core null\n");
            return 0;
        }
        std::printf("core ok\n");
        std::printf("memory %zu %zu\n", host_.bytes_given(), host_.blocks_given());
        print_error();
        uint32_t count;
        {
            guard::InCore inside;
            count = odrig_core_leg_count(core_);
        }
        for (uint32_t index = 0; index <= count; ++index) {
            odrig_leg leg;
            int found;
            {
                guard::InCore inside;
                found = odrig_core_leg(core_, index, &leg);
            }
            if (found != (index < count ? 1 : 0)) {
                stop("the leg list and its count disagree", 1);
            }
            if (found) {
                std::printf("leg %u %u %u\n", leg.leg, leg.pin, leg.led_count);
            }
        }
        std::printf("ready\n");

        std::string line;
        while (std::getline(script, line)) {
            if (!obey(line)) {
                std::printf("bad line\n");
                return kUsage;
            }
        }
        return 0;
    }

private:
    bool obey(const std::string &line) {
        if (line == "error") {
            print_error();
            return true;
        }
        return false;
    }

    void print_error() {
        const char *text;
        {
            guard::InCore inside;
            text = odrig_core_error(core_);
        }
        std::printf("error %s\n", text != nullptr ? text : "none");
    }

    Host host_;
    odrig_core *core_ = nullptr;
};

// Does what the guard must stop: asks the host for memory, or the program, as the core
// would after startup.
int guard_check(const std::string &what) {
    Host host = Host::of_memory("");
    odrig_host functions = host.interface();
    guard::InCore inside;
    if (what == "alloc") {
        functions.alloc(functions.ctx, 16);
    } else {
        char *volatile block = new char[1];
        delete[] block;
    }
    std::printf("the guard let it pass\n");
    return 1;
}

// Runs one session for each job of a batch on standard input. A job is the number of its
// files as text, then a name and a content for each file, then its script. After the lines
// of each session comes the line `end`.
int sessions(const Options &options) {
    std::vector<std::string> pieces = batch(standard_input());
    size_t at = 0;
    while (at < pieces.size()) {
        size_t count = static_cast<size_t>(std::atol(pieces[at++].c_str()));
        if (pieces.size() - at < 2 * count + 1) {
            stop("bad batch", kUsage);
        }
        std::map<std::string, std::string> files;
        for (size_t file = 0; file < count; ++file) {
            files[pieces[at]] = pieces[at + 1];
            at += 2;
        }
        std::istringstream script(pieces[at++]);
        int status = Session(Host::of_files(files, options)).run(script);
        if (status != 0) {
            return status;
        }
        std::printf("end\n");
    }
    return 0;
}

bool whole_number(const std::string &text, long *value) {
    if (text.empty() || text.size() > 9 || text.find_first_not_of("0123456789") != std::string::npos) {
        return false;
    }
    *value = std::atol(text.c_str());
    return true;
}

}  // namespace

int main(int argc, char **argv) {
    std::vector<std::string> arguments(argv + 1, argv + argc);
    if (arguments.empty()) {
        return usage();
    }
    const std::string &invocation = arguments[0];
    if (invocation == "reasons" && arguments.size() == 1) {
        return reasons();
    }
    if (invocation == "inflate" && arguments.size() == 1) {
        return inflate(false);
    }
    if (invocation == "inflate" && arguments.size() == 2 && arguments[1] == "--batch") {
        return inflate(true);
    }
    if (invocation == "decode" && arguments.size() == 2) {
        return decode(arguments[1]);
    }
    if (invocation == "guard" && arguments.size() == 2 && (arguments[1] == "alloc" || arguments[1] == "new")) {
        return guard_check(arguments[1]);
    }
    if (invocation == "session" && arguments.size() >= 2) {
        Options options;
        size_t at = 2;
        while (at < arguments.size()) {
            if (arguments[at] == "--alloc-fails-at" && at + 1 < arguments.size() &&
                whole_number(arguments[at + 1], &options.alloc_fails_at)) {
                at += 2;
            } else if (arguments[at] == "--read-fails" && at + 2 < arguments.size() &&
                       whole_number(arguments[at + 2], &options.read_fails_offset)) {
                options.read_fails_file = arguments[at + 1];
                at += 3;
            } else if (arguments[at] == "--trace-files") {
                options.trace_files = true;
                at += 1;
            } else {
                return usage();
            }
        }
        if (arguments[1] == "--batch") {
            return sessions(options);
        }
        return Session(Host::of_folder(arguments[1], options)).run(std::cin);
    }
    return usage();
}
