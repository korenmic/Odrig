#pragma once

#include <stddef.h>
#include <stdint.h>

namespace OdrigBootstrap {
enum Result { kExisting, kInitialized, kRetry };

const char kFolder[] = "fresh-init";
const char kPart[] = "fresh.part";
const char kMapping[] =
    "{\"version\":1,\"height\":60,\"legs\":["
    "{\"leg\":1,\"pin\":1,\"first_led\":\"bottom\",\"columns\":[1,2,3]},"
    "{\"leg\":2,\"pin\":2,\"first_led\":\"bottom\",\"columns\":[4,5,6]},"
    "{\"leg\":3,\"pin\":3,\"first_led\":\"bottom\",\"columns\":[7,8,9]},"
    "{\"leg\":4,\"pin\":4,\"first_led\":\"bottom\",\"columns\":[10,11,12]},"
    "{\"leg\":5,\"pin\":5,\"first_led\":\"bottom\",\"columns\":[13,14,15]},"
    "{\"leg\":6,\"pin\":6,\"first_led\":\"bottom\",\"columns\":[16,17,18]},"
    "{\"leg\":7,\"pin\":7,\"first_led\":\"bottom\",\"columns\":[19,20,21]},"
    "{\"leg\":8,\"pin\":8,\"first_led\":\"bottom\",\"columns\":[22,23,24]},"
    "{\"leg\":9,\"pin\":9,\"first_led\":\"bottom\",\"columns\":[25,26,27]},"
    "{\"leg\":10,\"pin\":10,\"first_led\":\"bottom\",\"columns\":[28,29,30]},"
    "{\"leg\":11,\"pin\":11,\"first_led\":\"bottom\",\"columns\":[31,32,33]},"
    "{\"leg\":12,\"pin\":12,\"first_led\":\"bottom\",\"columns\":[34,35,36]},"
    "{\"leg\":13,\"pin\":13,\"first_led\":\"bottom\",\"columns\":[37,38,39]},"
    "{\"leg\":14,\"pin\":14,\"first_led\":\"bottom\",\"columns\":[40,41,42]},"
    "{\"leg\":15,\"pin\":15,\"first_led\":\"bottom\",\"columns\":[43,44,45]},"
    "{\"leg\":16,\"pin\":16,\"first_led\":\"bottom\",\"columns\":[46,47,48]},"
    "{\"leg\":17,\"pin\":17,\"first_led\":\"bottom\",\"columns\":[49,50,51]},"
    "{\"leg\":18,\"pin\":18,\"first_led\":\"bottom\",\"columns\":[52,53,54]},"
    "{\"leg\":19,\"pin\":21,\"first_led\":\"bottom\",\"columns\":[55,56,57]},"
    "{\"leg\":20,\"pin\":47,\"first_led\":\"bottom\",\"columns\":[58,59,60]}]}\n";
const char kShow[] = "{\"version\":1,\"brightness\":32,\"items\":[]}\n";

template <class Store>
bool install(Store &store, const char *name, const char *text, size_t length) {
    if (store.kind(name) != 0) return store.equals(name, text, length);
    return store.write(kPart, text, length) && store.equals(kPart, text, length) &&
        store.kind(name) == 0 && store.rename(kPart, name) && store.equals(name, text, length);
}

// The empty marker directory is committed before any default file. Its presence
// lets a restart finish a partial initialization; unexpected data always wins.
template <class Store> Result initialize(Store &store) {
    const int root = store.kind("");
    if (root != 0 && root != 2) return kRetry;
    const int marker = store.kind(kFolder);
    if (marker == 0) {
        if (root == 2 && !store.only(nullptr, 0)) return kExisting;
        if (root == 0 && !store.mkdir("")) return kRetry;
        if (!store.mkdir(kFolder)) return kRetry;
    } else if (marker != 2 || !store.empty(kFolder)) {
        return kExisting;
    }
    const char *const allowed[] = {kFolder, kPart, "mapping.json", "show.json", "rotation.txt", "rotation.part"};
    if (!store.only(allowed, sizeof allowed / sizeof *allowed) || store.kind(kPart) > 1) return kExisting;
    const char *const names[] = {"mapping.json", "show.json"};
    const char *const texts[] = {kMapping, kShow};
    const size_t lengths[] = {sizeof kMapping - 1, sizeof kShow - 1};
    for (size_t i = 0; i < 2; ++i) {
        const int kind = store.kind(names[i]);
        if (kind != 0 && (kind != 1 || !store.equals(names[i], texts[i], lengths[i]))) return kExisting;
    }
    for (size_t i = 0; i < 2; ++i) {
        if (!install(store, names[i], texts[i], lengths[i])) return kRetry;
    }
    if (store.kind(kPart) != 0 && !store.remove(kPart)) return kRetry;
    return store.rmdir(kFolder) ? kInitialized : kRetry;
}
}
