// The test host: a program around the core that the suite of tests/core drives as a child
// process. It has no clock; whatever it prints depends on its arguments and its input only.

#include <sys/stat.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>

#include <filesystem>
#else
#include <dirent.h>
#include <unistd.h>
#endif

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "core_state.h"
#include "file_source.h"
#include "guard.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "odrig_core.h"
#include "reasons.h"

#ifndef S_ISREG
#define S_ISREG(mode) (((mode) & S_IFMT) == S_IFREG)
#endif

#ifdef _WIN32
// The call of Windows that renames a file over one that is there, as `rename` does on
// other systems. Its last argument, 1, says to take the place of what is there.
extern "C" __declspec(dllimport) int __stdcall MoveFileExA(const char *from, const char *to, unsigned long flags);
#endif

namespace {

const int kUsage = 64;
const int kFileMisuse = 71;
const int kBadReply = 72;
const int kPowerCut = 75;

// The storage of the board: the size of its partition and of a block of its file system.
const uint64_t kBoardStorage = 13500416;
const uint64_t kStorageBlock = 4096;

int usage() {
    std::fputs(
        "usage: odrig_host reasons\n"
        "       odrig_host inflate [--batch]\n"
        "       odrig_host decode [--slice BYTES] FILE | --batch\n"
        "       odrig_host session DIR | --batch [options]\n"
        "       odrig_host guard alloc | new | read | write | write-none | close-none | two-files\n"
        "                        | name | rename-open | remove-open | read-at | read-at-offset\n"
        "options of a session:\n"
        "       --alloc-fails-at N  --dirty-memory  --trace-files  --trace-reads  --trace-calls  --check-first\n"
        "       --read-fails FILE OFFSET  --read-fails-after FILE OFFSET N\n"
        "       --remove-after FILE N  --swap-after FILE N OTHER\n"
        "       --storage BYTES  --no-storage  --only-space  --space-unknown\n"
        "       --store-fails-at N  --cut-at N  --cut-keeps K  --trace-store\n"
        "       --read-back-fails OFFSET  --read-back-differs OFFSET\n"
        "       --drive DIR  --drive-pulled  --drive-read-fails NAME OFFSET\n",
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
    bool dirty_memory = false;      // hand out memory filled with the byte 0xA5, not zeroed
    std::string read_fails_file;    // the file whose reading fails,
    long read_fails_offset = 0;     // the offset at which `read` returns -1,
    long read_fails_after = 0;      // and the number of openings that are spared; with
                                    // none spared, `read_at` fails at that offset too
    std::string remove_after_file;  // the file that is gone
    long remove_after = 0;          // once it has been opened this many times
    std::string swap_after_file;    // the file under whose name
    long swap_after = 0;            // after this many openings
    std::string swap_other;         // the content of this other file is served
    bool trace_files = false;       // print `open <name> <result>` for every `open`
    bool trace_reads = false;       // print `read <name> <bytes>` for every `close`: what `read` gave of the file
    uint64_t storage = kBoardStorage;   // the total space `space` reports
    bool no_storage = false;        // the seven storage functions are null pointers
    bool only_space = false;        // of the seven, only `space` is there
    bool space_unknown = false;     // `space` returns -1
    long store_fails_at = 0;        // the number of the storage call that fails; 0 for none
    long cut_at = 0;                // the number of the storage call at which the power is cut
    long cut_keeps = 0;             // the bytes of that call that are written first, for a `write`
    bool trace_store = false;       // print `store <call> <arguments> <result>` for every storage call
    long read_back_fails = -1;      // of the uploaded file: the offset from which `read_at` returns -1; none below 0
    long read_back_differs = -1;    // of the uploaded file: the offset of the byte `read_at` gives with one bit changed
    bool check_names = false;       // stop when the core names a file outside its names
    bool check_first = false;       // let the check after the start end before the session
    std::string drive;              // the folder that stands for the top of a drive; none when empty
    bool drive_pulled = false;      // the drive is not plugged in at the start
    std::string drive_read_fails_file;  // the file of the drive whose reading with `read`
    long drive_read_fails_offset = 0;   // fails at this offset; `read_at` reads it whole
    bool trace_calls = false;       // print `call <bytes>` after every poll and command: what `read` and `read_at` gave in it
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
        const bool changes = from_ != kFromMemory && !options_.no_storage && !options_.only_space;
        functions.write_open = changes ? write_open : nullptr;
        functions.write = changes ? write : nullptr;
        functions.write_close = changes ? write_close : nullptr;
        functions.rename = changes ? rename : nullptr;
        functions.remove = changes ? remove : nullptr;
        functions.space = from_ != kFromMemory && !options_.no_storage ? space : nullptr;
        functions.read_at = changes ? read_at : nullptr;
        const bool drive = changes && !options_.drive.empty();
        functions.drive = drive ? drive_number : nullptr;
        functions.drive_name = drive ? drive_name : nullptr;
        functions.drive_space = nullptr;
        if (drive && !options_.drive_pulled) {
            plug();
        }
        return functions;
    }

    // The drive: plugged in, with a new number and the list of its folder `odrig` as it is
    // now, or pulled out. A drive plugged in with a folder stands for that folder from then
    // on.
    void plug(const std::string &top = std::string()) {
        if (!top.empty()) {
            options_.drive = top;
        }
        drive_names_.clear();
        const std::string folder = options_.drive + "/odrig";
#ifdef _WIN32
        std::error_code failed;
        for (const auto &entry : std::filesystem::directory_iterator(folder, failed)) {
            if (entry.is_regular_file(failed)) {
                drive_names_.push_back(entry.path().filename().string());
            }
        }
#else
        if (DIR *opened = opendir(folder.c_str())) {
            while (const dirent *entry = readdir(opened)) {
                struct stat status;
                if (stat((folder + "/" + entry->d_name).c_str(), &status) == 0 && S_ISREG(status.st_mode)) {
                    drive_names_.push_back(entry->d_name);
                }
            }
            closedir(opened);
        }
#endif
        // Files whose names end in `.odrg`, in any case, and do not begin with a dot, in the
        // order of their names, the first 256.
        std::vector<std::string> kept;
        for (const std::string &name : drive_names_) {
            std::string ending = name.size() >= 5 ? name.substr(name.size() - 5) : "";
            for (char &letter : ending) {
                letter = static_cast<char>(std::tolower(static_cast<unsigned char>(letter)));
            }
            if (name[0] != '.' && ending == ".odrg") {
                kept.push_back(name);
            }
        }
        std::sort(kept.begin(), kept.end());
        if (kept.size() > 256) {
            kept.resize(256);
        }
        drive_names_ = kept;
        drive_number_ = ++drives_plugged_;
    }

    void pull() {
        drive_number_ = 0;
        drive_names_.clear();
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
        void *block = std::malloc(bytes != 0 ? bytes : 1);
        if (block == nullptr) {
            std::abort();
        }
        std::memset(block, host.options_.dirty_memory ? 0xA5 : 0, bytes);
        host.blocks_.push_back(block);
        host.bytes_given_ += bytes;
        return block;
    }

    static uint32_t drive_number(void *ctx) {
        guard::InHost lowered;
        return static_cast<Host *>(ctx)->drive_number_;
    }

    static int drive_name(void *ctx, uint32_t drive, uint32_t place, char *buffer, size_t capacity) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (buffer == nullptr || capacity == 0) {
            stop("file misuse", kFileMisuse);
        }
        if (drive == 0 || drive != host.drive_number_ || place >= host.drive_names_.size()) {
            return 0;
        }
        const std::string &name = host.drive_names_[place];
        const size_t length = std::min(name.size(), capacity - 1);
        std::memcpy(buffer, name.data(), length);
        buffer[length] = '\0';
        return 1;
    }

    // The file of the drive a name `drive/<place>` stands for, or an empty text when the
    // drive has no file at that place.
    std::string drive_file(const char *name) const {
        const char *place = name + 6;
        size_t at = 0;
        for (const char *digit = place; *digit != '\0'; ++digit) {
            at = at * 10 + static_cast<size_t>(*digit - '0');
        }
        return drive_number_ != 0 && at < drive_names_.size() ? drive_names_[at] : "";
    }

    // Reads a file of the drive whole. False when there is none.
    bool drive_content(const char *name, std::string *content) const {
        const std::string file = drive_file(name);
        if (file.empty()) {
            return false;
        }
        std::FILE *opened = std::fopen((options_.drive + "/odrig/" + file).c_str(), "rb");
        if (opened == nullptr) {
            return false;
        }
        content->clear();
        char buffer[65536];
        size_t count;
        while ((count = std::fread(buffer, 1, sizeof buffer, opened)) > 0) {
            content->append(buffer, count);
        }
        std::fclose(opened);
        return true;
    }

    static bool of_the_drive(const char *name) { return std::strncmp(name, "drive/", 6) == 0; }

    static int open(void *ctx, const char *name) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (host.is_open_) {
            stop("file misuse", kFileMisuse);
        }
        host.check_name(name);
        if (of_the_drive(name)) {
            if (!host.drive_content(name, &host.content_)) {
                return 0;
            }
            host.is_open_ = true;
            host.open_name_ = name;
            host.read_fails_now_ = !host.options_.drive_read_fails_file.empty() && host.drive_file(name) == host.options_.drive_read_fails_file;
            host.fails_at_ = static_cast<size_t>(host.options_.drive_read_fails_offset);
            host.offset_ = 0;
            host.reads_ = 0;
            return 1;
        }
        // What the name stands for now: nothing once the file is removed, another file
        // once it is swapped.
        const Options &options = host.options_;
        long &openings = host.openings_[name];
        std::string source = name;
        bool removed = name == options.remove_after_file && openings >= options.remove_after;
        if (name == options.swap_after_file && openings >= options.swap_after) {
            source = options.swap_other;
        }
        int found = 1;
        if (removed) {
            found = 0;
        } else if (host.from_ == kFromMemory) {
            host.content_ = host.memory_;
        } else if (host.from_ == kFromFiles) {
            auto file = host.files_.find(source);
            found = file != host.files_.end() ? 1 : 0;
            if (found) {
                host.content_ = file->second;
            }
        } else {
            found = host.load(source.c_str());
        }
        if (options.trace_files) {
            std::printf("open %s %d\n", name, found);
        }
        if (found != 1) {
            return found;
        }
        ++openings;
        host.is_open_ = true;
        host.open_name_ = name;
        host.read_fails_now_ = name == options.read_fails_file && openings > options.read_fails_after;
        host.fails_at_ = static_cast<size_t>(options.read_fails_offset);
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
        if (host.read_fails_now_) {
            const size_t fails_at = host.fails_at_;
            if (host.offset_ >= fails_at) {
                return -1;
            }
            count = std::min(count, fails_at - host.offset_);
        }
        std::memcpy(buffer, host.content_.data() + host.offset_, count);
        host.offset_ += count;
        host.call_bytes_ += count;
        return static_cast<int32_t>(count);
    }

    static void close(void *ctx) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (!host.is_open_) {
            stop("file misuse", kFileMisuse);
        }
        host.is_open_ = false;
        if (host.options_.trace_reads) {
            std::printf("read %s %zu\n", host.open_name_.c_str(), host.offset_);
        }
    }

    static void log(void *, const char *text) {
        guard::InHost lowered;
        std::printf("log %s\n", text);
    }

    // The storage functions. A storage call is one of `write_open`, `write`, `write_close`,
    // `rename` and `remove`: these are counted, may fail or be where the power is cut, and
    // are traced.

    static int write_open(void *ctx, const char *name) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        host.check_name(name);
        if (host.writing_) {
            stop("file misuse", kFileMisuse);
        }
        int result = -1;
        if (host.store_call()) {
            result = host.begin_file(name) ? 1 : -1;
        }
        if (result == 1) {
            host.writing_ = true;
            host.writing_name_ = name;
        }
        host.trace("write_open", name, result);
        return result;
    }

    static int write(void *ctx, const uint8_t *bytes, size_t length) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (!host.writing_ || length == 0 || length > 1500) {
            stop("file misuse", kFileMisuse);
        }
        ++host.store_calls_;
        if (host.store_calls_ == host.options_.cut_at) {
            host.add_bytes(bytes, std::min(length, static_cast<size_t>(host.options_.cut_keeps)));
            stop("power cut", kPowerCut);
        }
        int result = -1;
        if (host.store_calls_ != host.options_.store_fails_at) {
            result = host.add_bytes(bytes, length) ? 1 : -1;
        }
        host.trace("write", std::to_string(length), result);
        return result;
    }

    static int write_close(void *ctx) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (!host.writing_) {
            stop("file misuse", kFileMisuse);
        }
        int result = -1;
        if (host.store_call()) {
            result = host.end_file() ? 1 : -1;
            host.writing_ = false;
        }
        host.trace("write_close", "", result);
        return result;
    }

    static int rename(void *ctx, const char *from, const char *to) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        host.check_name(from);
        host.check_name(to);
        if (host.holds(from) || host.holds(to)) {
            stop("file misuse", kFileMisuse);
        }
        int result = -1;
        if (host.store_call()) {
            result = host.rename_file(from, to) ? 1 : -1;
        }
        host.trace("rename", std::string(from) + " " + to, result);
        return result;
    }

    static int remove(void *ctx, const char *name) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        host.check_name(name);
        if (host.is_open_ && host.open_name_ == name) {
            stop("file misuse", kFileMisuse);
        }
        int result = -1;
        if (host.store_call()) {
            if (host.writing_ && host.writing_name_ == name) {
                host.end_file();
                host.writing_ = false;
            }
            result = host.remove_file(name);
        }
        host.trace("remove", name, result);
        return result;
    }

    static int space(void *ctx, uint32_t *free_bytes, uint32_t *total_bytes) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        if (host.options_.space_unknown) {
            return -1;
        }
        const uint64_t total = host.options_.storage;
        const uint64_t used = host.used_bytes();
        *total_bytes = static_cast<uint32_t>(total);
        *free_bytes = static_cast<uint32_t>(used < total ? total - used : 0);
        return 1;
    }

    static int32_t read_at(void *ctx, const char *name, uint32_t offset, uint8_t *buffer, size_t capacity) {
        guard::InHost lowered;
        Host &host = *static_cast<Host *>(ctx);
        host.check_name(name);
        const bool goes_on = host.read_at_name_ == name && offset == host.read_at_end_;
        if (capacity == 0 || capacity > 512 || (offset != 0 && !goes_on)) {
            stop("file misuse", kFileMisuse);
        }
        std::string content;
        if (of_the_drive(name) ? !host.drive_content(name, &content) : !host.whole_file(name, &content)) {
            return -1;
        }
        size_t count = kReadSizes[host.reads_at_++ % (sizeof kReadSizes / sizeof kReadSizes[0])];
        count = std::min(count, capacity);
        count = offset < content.size() ? std::min(count, content.size() - offset) : 0;
        const Options &options = host.options_;
        const bool uploaded = std::strcmp(name, "upload.part") == 0;
        if (name == options.read_fails_file && options.read_fails_after == 0) {
            // As `read` does: no byte at or after the offset, and no end of the file there.
            const size_t fails_at = static_cast<size_t>(options.read_fails_offset);
            if (offset >= fails_at) {
                return -1;
            }
            count = std::min(count, fails_at - offset);
        }
        const long fails = uploaded ? options.read_back_fails : -1;
        if (fails >= 0 && offset + count > static_cast<size_t>(fails)) {
            if (offset >= static_cast<size_t>(fails)) {
                return -1;
            }
            count = static_cast<size_t>(fails) - offset;
        }
        const long differs = uploaded ? options.read_back_differs : -1;
        if (differs >= 0 && static_cast<size_t>(differs) < content.size()) {
            content[static_cast<size_t>(differs)] = static_cast<char>(content[static_cast<size_t>(differs)] ^ 0x01);
        }
        std::memcpy(buffer, content.data() + (count != 0 ? offset : 0), count);
        host.read_at_name_ = name;
        host.read_at_end_ = offset + static_cast<uint32_t>(count);
        host.call_bytes_ += count;
        return static_cast<int32_t>(count);
    }

    // Stops the program when a name the core gives is not one of its names: 1 to 32
    // characters of a-z, 0-9, `-`, `_` and `.`, and either the name of an `.odrg` file or
    // one of the eight fixed names.
    void check_name(const char *name) const {
        if (!options_.check_names) {
            return;
        }
        const std::string given = name;
        if (!options_.drive.empty() && of_the_drive(name) && given.size() > 6 &&
            given.find_first_not_of("0123456789", 6) == std::string::npos) {
            return;
        }
        bool sound = !given.empty() && given.size() <= 32 &&
                     given.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789-_.") == std::string::npos;
        const bool animation = given.size() >= 5 && given.compare(given.size() - 5, 5, ".odrg") == 0;
        const bool fixed = given == "mapping.json" || given == "show.json" || given == "upload.part" ||
                           given == "show.part" || given == "pending.txt" || given == "mapping.part" ||
                           given == "order.txt" || given == "order.part";
        if (!sound || !(animation || fixed)) {
            stop("file misuse", kFileMisuse);
        }
    }

    // Counts a storage call that is no `write`. False when this one fails. The program
    // ends here when this one is where the power is cut.
    bool store_call() {
        ++store_calls_;
        if (store_calls_ == options_.cut_at) {
            stop("power cut", kPowerCut);
        }
        return store_calls_ != options_.store_fails_at;
    }

    void trace(const char *call, const std::string &arguments, int result) const {
        if (options_.trace_store) {
            std::printf("store %s%s%s %d\n", call, arguments.empty() ? "" : " ", arguments.c_str(), result);
        }
    }

    // Whether a name is the file that `open` holds or the one being written.
    bool holds(const char *name) const {
        return (is_open_ && open_name_ == name) || (writing_ && writing_name_ == name);
    }

    std::string path_of(const std::string &name) const { return folder_ + "/" + name; }

    // The files as they are stored: in the folder, or in the set held in memory.

    bool begin_file(const char *name) {
        if (from_ == kFromFiles) {
            files_[name].clear();
            return true;
        }
        written_ = std::fopen(path_of(name).c_str(), "wb");
        return written_ != nullptr;
    }

    // Adds bytes to the file being written, so that they are there when the program ends.
    bool add_bytes(const uint8_t *bytes, size_t length) {
        if (from_ == kFromFiles) {
            files_[writing_name_].append(reinterpret_cast<const char *>(bytes), length);
            return true;
        }
        return std::fwrite(bytes, 1, length, written_) == length && std::fflush(written_) == 0;
    }

    bool end_file() {
        if (from_ == kFromFiles) {
            return true;
        }
        std::FILE *file = written_;
        written_ = nullptr;
        return file != nullptr && std::fclose(file) == 0;
    }

    bool rename_file(const char *from, const char *to) {
        if (from_ == kFromFiles) {
            auto file = files_.find(from);
            if (file == files_.end()) {
                return false;
            }
            std::string content = file->second;
            files_.erase(file);
            files_[to] = content;
            return true;
        }
#ifdef _WIN32
        return MoveFileExA(path_of(from).c_str(), path_of(to).c_str(), 1) != 0;
#else
        return ::rename(path_of(from).c_str(), path_of(to).c_str()) == 0;
#endif
    }

    // 1 when a file was removed, 0 when there was none, -1 otherwise.
    int remove_file(const char *name) {
        if (from_ == kFromFiles) {
            return files_.erase(name) != 0 ? 1 : 0;
        }
#ifdef _WIN32
        if (std::remove(path_of(name).c_str()) == 0) {
            return 1;
        }
#else
        if (::unlink(path_of(name).c_str()) == 0) {
            return 1;
        }
#endif
        return errno == ENOENT ? 0 : -1;
    }

    bool whole_file(const char *name, std::string *content) {
        if (from_ == kFromFiles) {
            auto file = files_.find(name);
            if (file == files_.end()) {
                return false;
            }
            *content = file->second;
            return true;
        }
        std::string kept = content_;
        const bool loaded = load(name) == 1;
        *content = content_;
        content_ = kept;
        return loaded;
    }

    // The space the files take: the size of each, rounded up to a whole block.
    uint64_t used_bytes() const {
        uint64_t used = 0;
        if (from_ == kFromFiles) {
            for (const auto &file : files_) {
                used += (file.second.size() + kStorageBlock - 1) / kStorageBlock * kStorageBlock;
            }
            return used;
        }
#ifdef _WIN32
        std::error_code failed;
        for (const auto &entry : std::filesystem::directory_iterator(folder_, failed)) {
            if (entry.is_regular_file(failed)) {
                used += (static_cast<uint64_t>(entry.file_size(failed)) + kStorageBlock - 1) / kStorageBlock * kStorageBlock;
            }
        }
        return used;
#else
        DIR *folder = opendir(folder_.c_str());
        if (folder == nullptr) {
            return 0;
        }
        while (const dirent *entry = readdir(folder)) {
            struct stat status;
            if (stat(path_of(entry->d_name).c_str(), &status) == 0 && S_ISREG(status.st_mode)) {
                used += (static_cast<uint64_t>(status.st_size) + kStorageBlock - 1) / kStorageBlock * kStorageBlock;
            }
        }
        closedir(folder);
        return used;
#endif
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

public:
    bool checks_first() const { return options_.check_first; }
    bool has_drive() const { return !options_.drive.empty(); }
    bool traces_calls() const { return options_.trace_calls; }
    From from_ = kFromFolder;
    std::string folder_;
    std::map<std::string, std::string> files_;
    std::string memory_;

    std::string content_;
    std::string open_name_;
    std::map<std::string, long> openings_;
    bool read_fails_now_ = false;
    size_t fails_at_ = 0;
    uint32_t drive_number_ = 0;
    uint32_t drives_plugged_ = 0;
    std::vector<std::string> drive_names_;
    bool is_open_ = false;
    size_t offset_ = 0;
    size_t reads_ = 0;

    bool writing_ = false;
    std::string writing_name_;
    std::FILE *written_ = nullptr;
    long store_calls_ = 0;
    std::string read_at_name_;
    uint32_t read_at_end_ = 0;
    size_t reads_at_ = 0;

    long alloc_calls_ = 0;
    size_t bytes_given_ = 0;
    std::vector<void *> blocks_;
    uint64_t call_bytes_ = 0;       // what `read` and `read_at` gave since the last call's end
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
// refused, `rejected <reason>`. The decoder is called again while it settles a defect. With
// a slice, settling takes at most that many bytes in one call, and `pending <calls>`, the
// calls that gave kPendingWork, comes before the last line.
void decode_one(Host &host, const char *name, uint32_t slice) {
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
        if (slice != 0) {
            decoder.settle_slice = slice;
        }
    }
    unsigned long pending = 0;
    if (reason == odrig::kNone) {
        std::printf("header %u %u %u %u %u\n", decoder.width, decoder.height, decoder.colours,
                    decoder.frames, decoder.compressed);
        std::vector<uint8_t> pixels(decoder.n, 0);
        std::string picture;
        for (uint32_t record = 0; record < decoder.frames && reason == odrig::kNone; ++record) {
            uint16_t duration = 0;
            while ((reason = decoder.next(pixels.data(), &duration)) == odrig::kPendingWork) {
                ++pending;
            }
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
            while ((reason = decoder.finish()) == odrig::kPendingWork) {
                ++pending;
            }
        }
    }
    file.close();
    if (slice != 0) {
        std::printf("pending %lu\n", pending);
    }
    if (reason == odrig::kNone) {
        std::printf("end\n");
    } else {
        std::printf("rejected %s\n", odrig::reason_name(reason));
    }
}

// Where the name of a file begins in a path: after its last separator. On Windows a
// backslash separates as a slash does.
size_t last_separator(const std::string &path) {
#ifdef _WIN32
    return path.find_last_of("/\\");
#else
    return path.rfind('/');
#endif
}

int decode(const std::string &argument, uint32_t slice) {
    if (argument == "--batch") {
        for (const std::string &content : batch(standard_input())) {
            Host host = Host::of_memory(content);
            decode_one(host, "file.odrg", slice);
        }
        return 0;
    }
    size_t slash = last_separator(argument);
    std::string folder = slash == std::string::npos ? "." : argument.substr(0, slash);
    std::string name = slash == std::string::npos ? argument : argument.substr(slash + 1);
    Host host = Host::of_folder(folder);
    decode_one(host, name.c_str(), slice);
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
        if (host_.checks_first()) {
            // The check after the start takes its steps here, with no refresh between
            // them, so that the session begins with every file read to its end, those of
            // a drive that is plugged in too.
            guard::InCore inside;
            odrig::drive_touch(core_->state);
            while (!core_->state.invalid &&
                   (!odrig::check_complete(core_->state) || odrig::drive_waits(core_->state))) {
                odrig::check_after_start(core_->state, true, true);
            }
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
        refuse_a_small_reply();
        std::printf("ready\n");
        // What the start read is no call's.
        host_.call_bytes_ = 0;

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
        if (line == "fault") {
            print_fault();
            return true;
        }
        if (line == "drive plug" || line == "drive pull" || line.rfind("drive plug ", 0) == 0) {
            if (!host_.has_drive()) {
                return false;
            }
            if (line == "drive pull") {
                host_.pull();
            } else {
                host_.plug(line.size() > 11 ? line.substr(11) : std::string());
            }
            return true;
        }
        size_t space = line.find(' ');
        std::string word = line.substr(0, space);
        std::string rest = space == std::string::npos ? "" : line.substr(space + 1);
        if (word == "poll") {
            uint64_t now;
            if (!timestamp(rest, &now)) {
                return false;
            }
            poll(now);
            return true;
        }
        if (word == "line" || word == "linehex" || word == "bytes") {
            // The timestamp, and after one space whatever the line is made of.
            size_t gap = rest.find(' ');
            std::string given = gap == std::string::npos ? "" : rest.substr(gap + 1);
            uint64_t now;
            if (!timestamp(rest.substr(0, gap), &now) || (word != "line" && !unhex(&given))) {
                return false;
            }
            if (word == "bytes") {
                feed(now, given);
            } else {
                command(now, given);
            }
            return true;
        }
        return false;
    }

    // A reply needs room for ODRIG_REPLY_MAX bytes. With less the core writes nothing,
    // returns 0 and does not take the call as one that carries a timestamp.
    void refuse_a_small_reply() {
        std::vector<char> small(ODRIG_REPLY_MAX - 1);
        const char line[] = "status";
        size_t length;
        {
            guard::InCore inside;
            length = odrig_core_command(core_, 0, line, 6, small.data(), small.size());
        }
        if (length != 0) {
            stop("a reply was written where there is too little room", 1);
        }
    }

    // `fault <work> <record> <bytes> <reason> <name>`: the context the core keeps of the
    // latest fault of a file; or `fault none`.
    void print_fault() {
        const odrig::FaultContext &fault = core_->state.fault;
        if (!fault.present) {
            std::printf("fault none\n");
            return;
        }
        static const char *const works[] = {"none", "start", "play", "upload", "drive"};
        std::printf("fault %s %u %llu %s %s\n", fault.work < 5 ? works[fault.work] : "?", fault.record,
                    static_cast<unsigned long long>(fault.body_bytes),
                    odrig::reason_name(static_cast<odrig::Reason>(fault.reason)), fault.name);
    }

    // Turns hexadecimal digits into the bytes they stand for.
    static bool unhex(std::string *text) {
        if (text->size() % 2 != 0 || text->find_first_not_of("0123456789abcdef") != std::string::npos) {
            return false;
        }
        std::string bytes;
        for (size_t at = 0; at < text->size(); at += 2) {
            bytes += static_cast<char>(std::stoi(text->substr(at, 2), nullptr, 16));
        }
        *text = bytes;
        return true;
    }

    // Prints `reply <json>` for a reply of the core. A reply that is not one line of
    // printable characters with a newline, of at most ODRIG_REPLY_MAX bytes, ends the program.
    static void print_reply(const char *reply, size_t length) {
        bool sound = length >= 2 && length <= ODRIG_REPLY_MAX && reply[length - 1] == '\n';
        for (size_t at = 0; sound && at + 1 < length; ++at) {
            sound = reply[at] >= 0x20 && reply[at] < 0x7F;
        }
        if (!sound) {
            stop("bad reply", kBadReply);
        }
        std::printf("reply %.*s\n", static_cast<int>(length - 1), reply);
    }

    // One command line. The line and the reply are held in blocks of exactly their sizes, so
    // that a byte read or written beyond either is reported.
    void command(uint64_t now, const std::string &text) {
        std::vector<char> line(text.begin(), text.end());
        std::vector<char> reply(ODRIG_REPLY_MAX);
        size_t length;
        {
            guard::InCore inside;
            length = odrig_core_command(core_, now, line.data(), line.size(), reply.data(), reply.size());
        }
        print_reply(reply.data(), length);
        trace_call();
    }

    // Bytes of a transport. Prints `fed <hex of the line>` and `reply <json>` for every
    // line the bytes complete.
    void feed(uint64_t now, const std::string &bytes) {
        std::vector<uint8_t> given(bytes.begin(), bytes.end());
        guard::InCore inside;
        odrig_core_feed(core_, now, given.data(), given.size(), on_reply, nullptr);
    }

    static void on_reply(void *, const char *line, size_t line_length, const char *reply, size_t reply_length) {
        guard::InHost lowered;
        if (line_length > ODRIG_LINE_MAX) {
            stop("bad reply", kBadReply);
        }
        std::printf("fed %s\n", hex(std::string(line, line_length)).c_str());
        print_reply(reply, reply_length);
    }

    // A timestamp: decimal digits, at most 19 of them.
    static bool timestamp(const std::string &text, uint64_t *value) {
        if (text.empty() || text.size() > 19 || text.find_first_not_of("0123456789") != std::string::npos) {
            return false;
        }
        *value = std::strtoull(text.c_str(), nullptr, 10);
        return true;
    }

    // With `--trace-calls`, prints what the call that has just ended read of files.
    void trace_call() {
        if (host_.traces_calls()) {
            std::printf("call %llu\n", static_cast<unsigned long long>(host_.call_bytes_));
        }
        host_.call_bytes_ = 0;
    }

    // `refresh <ms>` and the LED data of every leg, or `idle <ms>` when no refresh was due.
    void poll(uint64_t now) {
        int produced;
        {
            guard::InCore inside;
            produced = odrig_core_poll(core_, now);
        }
        trace_call();
        if (!produced) {
            std::printf("idle %llu\n", static_cast<unsigned long long>(now));
            return;
        }
        std::printf("refresh %llu\n", static_cast<unsigned long long>(now));
        uint32_t count;
        {
            guard::InCore inside;
            count = odrig_core_leg_count(core_);
        }
        for (uint32_t index = 0; index < count; ++index) {
            odrig_leg leg;
            {
                guard::InCore inside;
                odrig_core_leg(core_, index, &leg);
            }
            std::string rgb(reinterpret_cast<const char *>(leg.rgb), 3 * static_cast<size_t>(leg.led_count));
            std::printf("data %u %s\n", leg.leg, hex(rgb).c_str());
        }
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

// Does what the test host must stop: asks the host for memory, or the program, as the core
// would after startup; or asks the host for more of a file than 512 bytes at once.
int guard_check(const std::string &what) {
    Host host = Host::of_memory("content");
    odrig_host functions = host.interface();
    guard::InCore inside;
    if (what == "alloc") {
        functions.alloc(functions.ctx, 16);
    } else if (what == "new") {
        char *volatile block = new char[1];
        delete[] block;
    } else {
        uint8_t buffer[513];
        functions.open(functions.ctx, "file");
        functions.read(functions.ctx, buffer, sizeof buffer);
    }
    std::printf("the guard let it pass\n");
    return 1;
}

const char *const kStorageGuards[] = {"write", "write-none", "close-none", "two-files", "name",
                                      "rename-open", "remove-open", "read-at", "read-at-offset"};

bool is_storage_guard(const std::string &what) {
    for (const char *guard_name : kStorageGuards) {
        if (what == guard_name) {
            return true;
        }
    }
    return false;
}

// Uses the storage functions as the core never may: each of these stops the program.
int storage_guard_check(const std::string &what) {
    Options options;
    options.check_names = true;
    std::map<std::string, std::string> files;
    files["show.json"] = "{}";
    files["a.odrg"] = "0123456789";
    Host host = Host::of_files(files, options);
    odrig_host functions = host.interface();
    void *ctx = functions.ctx;
    uint8_t buffer[1501];
    std::memset(buffer, 0, sizeof buffer);
    guard::InCore inside;
    if (what == "write") {
        functions.write_open(ctx, "upload.part");
        functions.write(ctx, buffer, 1500);
        functions.write(ctx, buffer, 1501);
    } else if (what == "write-none") {
        functions.write(ctx, buffer, 1);
    } else if (what == "close-none") {
        functions.write_close(ctx);
    } else if (what == "two-files") {
        functions.write_open(ctx, "upload.part");
        functions.write_open(ctx, "show.part");
    } else if (what == "name") {
        functions.remove(ctx, "pending.txt");
        functions.remove(ctx, "a.odrg");
        functions.remove(ctx, "notes.txt");
    } else if (what == "rename-open") {
        functions.write_open(ctx, "upload.part");
        functions.write_close(ctx);
        functions.rename(ctx, "upload.part", "b.odrg");
        functions.open(ctx, "a.odrg");
        functions.rename(ctx, "b.odrg", "a.odrg");
    } else if (what == "remove-open") {
        functions.open(ctx, "a.odrg");
        functions.remove(ctx, "show.part");
        functions.remove(ctx, "a.odrg");
    } else if (what == "read-at") {
        functions.read_at(ctx, "a.odrg", 0, buffer, 512);
        functions.read_at(ctx, "a.odrg", 0, buffer, 513);
    } else {
        int32_t first = functions.read_at(ctx, "a.odrg", 0, buffer, 4);
        functions.read_at(ctx, "a.odrg", static_cast<uint32_t>(first), buffer, 4);
        functions.read_at(ctx, "a.odrg", 0, buffer, 4);
        functions.read_at(ctx, "a.odrg", 9, buffer, 4);
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

// A number of bytes of storage: decimal digits with a value up to 4,294,967,295.
bool storage_bytes(const std::string &text, uint64_t *value) {
    if (text.empty() || text.size() > 10 || text.find_first_not_of("0123456789") != std::string::npos) {
        return false;
    }
    *value = std::strtoull(text.c_str(), nullptr, 10);
    return *value <= 0xFFFFFFFFull;
}

}  // namespace

int main(int argc, char **argv) {
#ifdef _WIN32
    // The input and the output are bytes: no line ending is to be changed on the way.
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
    _setmode(_fileno(stderr), _O_BINARY);
#endif
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
        return decode(arguments[1], 0);
    }
    long slice = 0;
    if (invocation == "decode" && arguments.size() == 4 && arguments[1] == "--slice" &&
        whole_number(arguments[2], &slice) && slice > 0 && slice <= 0x7FFFFFFF) {
        return decode(arguments[3], static_cast<uint32_t>(slice));
    }
    if (invocation == "guard" && arguments.size() == 2 &&
        (arguments[1] == "alloc" || arguments[1] == "new" || arguments[1] == "read")) {
        return guard_check(arguments[1]);
    }
    if (invocation == "guard" && arguments.size() == 2 && is_storage_guard(arguments[1])) {
        return storage_guard_check(arguments[1]);
    }
    if (invocation == "session" && arguments.size() >= 2) {
        Options options;
        options.check_names = true;
        size_t at = 2;
        while (at < arguments.size()) {
            if (arguments[at] == "--alloc-fails-at" && at + 1 < arguments.size() &&
                whole_number(arguments[at + 1], &options.alloc_fails_at)) {
                at += 2;
            } else if (arguments[at] == "--read-fails" && at + 2 < arguments.size() &&
                       whole_number(arguments[at + 2], &options.read_fails_offset)) {
                options.read_fails_file = arguments[at + 1];
                at += 3;
            } else if (arguments[at] == "--read-fails-after" && at + 3 < arguments.size() &&
                       whole_number(arguments[at + 2], &options.read_fails_offset) &&
                       whole_number(arguments[at + 3], &options.read_fails_after)) {
                options.read_fails_file = arguments[at + 1];
                at += 4;
            } else if (arguments[at] == "--drive" && at + 1 < arguments.size()) {
                options.drive = arguments[at + 1];
                at += 2;
            } else if (arguments[at] == "--drive-pulled") {
                options.drive_pulled = true;
                at += 1;
            } else if (arguments[at] == "--drive-read-fails" && at + 2 < arguments.size() &&
                       whole_number(arguments[at + 2], &options.drive_read_fails_offset)) {
                options.drive_read_fails_file = arguments[at + 1];
                at += 3;
            } else if (arguments[at] == "--remove-after" && at + 2 < arguments.size() &&
                       whole_number(arguments[at + 2], &options.remove_after)) {
                options.remove_after_file = arguments[at + 1];
                at += 3;
            } else if (arguments[at] == "--swap-after" && at + 3 < arguments.size() &&
                       whole_number(arguments[at + 2], &options.swap_after)) {
                options.swap_after_file = arguments[at + 1];
                options.swap_other = arguments[at + 3];
                at += 4;
            } else if (arguments[at] == "--dirty-memory") {
                options.dirty_memory = true;
                at += 1;
            } else if (arguments[at] == "--trace-files") {
                options.trace_files = true;
                at += 1;
            } else if (arguments[at] == "--trace-reads") {
                options.trace_reads = true;
                at += 1;
            } else if (arguments[at] == "--trace-calls") {
                options.trace_calls = true;
                at += 1;
            } else if (arguments[at] == "--check-first") {
                options.check_first = true;
                at += 1;
            } else if (arguments[at] == "--storage" && at + 1 < arguments.size() &&
                       storage_bytes(arguments[at + 1], &options.storage)) {
                at += 2;
            } else if (arguments[at] == "--no-storage") {
                options.no_storage = true;
                at += 1;
            } else if (arguments[at] == "--only-space") {
                options.only_space = true;
                at += 1;
            } else if (arguments[at] == "--space-unknown") {
                options.space_unknown = true;
                at += 1;
            } else if (arguments[at] == "--store-fails-at" && at + 1 < arguments.size() &&
                       whole_number(arguments[at + 1], &options.store_fails_at)) {
                at += 2;
            } else if (arguments[at] == "--cut-at" && at + 1 < arguments.size() &&
                       whole_number(arguments[at + 1], &options.cut_at)) {
                at += 2;
            } else if (arguments[at] == "--cut-keeps" && at + 1 < arguments.size() &&
                       whole_number(arguments[at + 1], &options.cut_keeps)) {
                at += 2;
            } else if (arguments[at] == "--trace-store") {
                options.trace_store = true;
                at += 1;
            } else if (arguments[at] == "--read-back-fails" && at + 1 < arguments.size() &&
                       whole_number(arguments[at + 1], &options.read_back_fails)) {
                at += 2;
            } else if (arguments[at] == "--read-back-differs" && at + 1 < arguments.size() &&
                       whole_number(arguments[at + 1], &options.read_back_differs)) {
                at += 2;
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
