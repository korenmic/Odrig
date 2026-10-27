#include "current_limits.h"

#include "json_reader.h"

namespace odrig {

namespace {

// WLED's figures: an LED at full white draws 55 mA, red, green and blue at 255 each.
const uint64_t kLedMa = 55;
const uint64_t kFullWhite = 3 * 255;

// The halving over the levels 1 to 254 adds one bit of the level at each of its fades,
// from this one down.
const uint32_t kHighestBit = 128;

// While a refresh is limited, `limited` of a leg also says whether its own pass left it
// above its budget; the bit is cleared before the refresh ends.
const uint8_t kLimitedBit = 1;
const uint8_t kOverBit = 2;

const uint32_t kNameSize = 8;

// WLED's video fade of one byte to a level from 1 to 254, in an LED that is not black and
// whose largest byte, shifted right by two and with 1 added, is `kept`: a byte above it
// keeps its lowest bit set.
inline uint32_t faded(uint32_t byte, uint32_t level, uint32_t kept) {
    return ((byte * level + 127) >> 8) | (byte > kept ? 1u : 0u);
}

inline uint32_t kept_of(uint32_t red, uint32_t green, uint32_t blue) {
    uint32_t largest = red > green ? red : green;
    largest = largest > blue ? largest : blue;
    return (largest >> 2) + 1;
}

// The sum of the bytes of `leds` LEDs faded to a level from 1 to 254, without writing
// them.
uint32_t faded_sum(const uint8_t *data, uint32_t leds, uint32_t level) {
    uint32_t sum = 0;
    for (const uint8_t *end = data + 3u * leds; data != end; data += 3) {
        const uint32_t red = data[0], green = data[1], blue = data[2];
        if ((red | green | blue) == 0) {
            continue;
        }
        const uint32_t kept = kept_of(red, green, blue);
        sum += faded(red, level, kept) + faded(green, level, kept) + faded(blue, level, kept);
    }
    return sum;
}

// Fades the bytes of `leds` LEDs to a level from 1 to 254. An LED that is black stays so.
void fade(uint8_t *data, uint32_t leds, uint32_t level) {
    for (uint8_t *end = data + 3u * leds; data != end; data += 3) {
        const uint32_t red = data[0], green = data[1], blue = data[2];
        if ((red | green | blue) == 0) {
            continue;
        }
        const uint32_t kept = kept_of(red, green, blue);
        data[0] = static_cast<uint8_t>(faded(red, level, kept));
        data[1] = static_cast<uint8_t>(faded(green, level, kept));
        data[2] = static_cast<uint8_t>(faded(blue, level, kept));
    }
}

uint8_t *leg_data(const Core &core, const LegInfo &leg) {
    return core.led_data + 3u * leg.first;
}

// The level at which a budget dims bytes estimated at `estimate`, which `leds` LEDs make:
// 255 with no budget or an estimate within it; 1 when the budget is at most what the LEDs
// draw at rest; otherwise the largest level from 1 to 254 whose fade is estimated within
// the budget, and 1 when none is. `estimate_at` gives the estimate of the fade at a level.
// The halving adds one bit of the level at each fade, from 128 down, and keeps it when
// that fade is within the budget: as the level rises the estimate of the fade never
// falls. A level of 255 is the bytes as they are, above the budget.
template <typename EstimateAt>
uint32_t level_of(uint32_t budget, uint32_t estimate, uint32_t leds, EstimateAt estimate_at) {
    if (budget == 0 || estimate <= budget) {
        return kUndimmed;
    }
    if (budget <= leds) {
        return 1;
    }
    uint32_t found = 0;
    for (uint32_t bit = kHighestBit; bit != 0; bit >>= 1) {
        const uint32_t candidate = found + bit;
        if (candidate < kUndimmed && estimate_at(candidate) <= budget) {
            found = candidate;
        }
    }
    return found != 0 ? found : 1;
}

// The level of a leg's budget for its bytes as they are now, estimated at `estimate`.
uint32_t leg_level(const Core &core, const LegInfo &leg, uint32_t estimate) {
    const uint8_t *data = leg_data(core, leg);
    return level_of(leg.budget, estimate, leg.count,
                    [&](uint32_t level) { return limits_estimate(faded_sum(data, leg.count, level), leg.count); });
}

// The estimate of every leg's bytes faded to a level, the sum of the legs' estimates. It
// stops adding once the sum is above `budget`, which is all that is asked of it then.
uint32_t wall_estimate_at(const Core &core, uint32_t level, uint32_t budget) {
    uint32_t sum = 0;
    for (uint32_t index = 0; index < core.leg_count && sum <= budget; ++index) {
        const LegInfo &leg = core.legs[index];
        sum += limits_estimate(faded_sum(leg_data(core, leg), leg.count, level), leg.count);
    }
    return sum;
}

// Reads the whole budgets' file once, setting the budgets of the legs it names that the
// mapping has. False when it breaks a rule.
bool read_budgets(Core &core, JsonReader &json) {
    char name[kNameSize];
    uint32_t members = 0;
    // One bit for each leg number, to find one named twice.
    uint8_t named[32] = {};
    if (!json.object_begin()) {
        return false;
    }
    while (json.object_next(name, sizeof name)) {
        uint32_t member;
        if (same_text(name, "version")) {
            member = 1;
        } else if (same_text(name, "wall")) {
            member = 2;
        } else if (same_text(name, "legs")) {
            member = 4;
        } else {
            return false;
        }
        if ((members & member) != 0) {
            return false;
        }
        members |= member;

        if (member == 1) {
            uint32_t version;
            if (!json.integer(&version) || version != 1) {
                return false;
            }
        } else if (member == 2) {
            uint32_t wall;
            if (!json.integer(&wall) || wall > kLargestWallBudget) {
                return false;
            }
            core.wall_budget = wall;
        } else {
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                uint32_t leg;
                uint32_t budget;
                if (!json.array_begin() || !json.array_next() || !json.integer(&leg) || leg < 1 || leg > 255 ||
                    !json.array_next() || !json.integer(&budget) || budget > kLargestLegBudget || json.array_next()) {
                    return false;
                }
                const uint8_t bit = static_cast<uint8_t>(1u << (leg & 7));
                if ((named[leg >> 3] & bit) != 0) {
                    return false;
                }
                named[leg >> 3] |= bit;
                for (uint32_t index = 0; index < core.leg_count; ++index) {
                    if (core.legs[index].leg == leg) {
                        core.legs[index].budget = static_cast<uint16_t>(budget);
                    }
                }
            }
            if (json.failed) {
                return false;
            }
        }
    }
    return !json.failed && members == 7 && json.end();
}

// The defaults: every leg's budget 0, and the wall's the host's.
void use_defaults(Core &core) {
    core.wall_budget = core.wall_default;
    for (uint32_t index = 0; index < core.leg_count; ++index) {
        core.legs[index].budget = 0;
    }
    core.limits_saved = 0;
}

}  // namespace

uint32_t limits_estimate(uint32_t sum, uint32_t leds) {
    return static_cast<uint32_t>(static_cast<uint64_t>(sum) * kLedMa / kFullWhite) + leds;
}

uint32_t limits_sum(const uint8_t *data, uint32_t leds) {
    uint32_t sum = 0;
    for (const uint8_t *end = data + 3u * leds; data != end; ++data) {
        sum += *data;
    }
    return sum;
}

void limits_read(Core &core) {
    use_defaults(core);
    core.limits_present = 0;
    const Reason opened = core.file.open(core.host, kLimitsFile);
    if (opened == kFileMissing) {
        return;
    }
    core.limits_present = 1;
    bool sound = false;
    if (opened == kNone) {
        JsonReader json;
        json.start(&core.file);
        sound = read_budgets(core, json);
        core.file.close();
    }
    if (!sound) {
        use_defaults(core);
        if (core.host.log != nullptr) {
            core.host.log(core.host.ctx, "limits unreadable");
        }
        return;
    }
    core.limits_saved = 1;
}

void limits_apply(Core &core) {
    // Each leg by its own budget. Without a budget of the wall, a leg without one of its
    // own is neither estimated nor changed.
    const uint32_t budget = core.wall_budget;
    uint32_t wall_estimate = 0;
    uint32_t leds = 0;
    for (uint32_t index = 0; index < core.leg_count; ++index) {
        LegInfo &leg = core.legs[index];
        leg.limited = 0;
        leds += leg.count;
        if (leg.budget == 0 && budget == 0) {
            continue;
        }
        uint8_t *data = leg_data(core, leg);
        uint32_t estimate = limits_estimate(limits_sum(data, leg.count), leg.count);
        const uint32_t level = leg_level(core, leg, estimate);
        if (level < kUndimmed) {
            fade(data, leg.count, level);
            leg.limited = kLimitedBit;
            estimate = limits_estimate(limits_sum(data, leg.count), leg.count);
        }
        if (budget != 0 && leg.budget != 0 && estimate > leg.budget) {
            leg.limited |= kOverBit;
        }
        wall_estimate += estimate;
    }
    // Every leg by the wall's level.
    const uint32_t level = level_of(budget, wall_estimate, leds, [&](uint32_t at) { return wall_estimate_at(core, at, budget); });
    core.wall_limited = level < kUndimmed ? 1 : 0;
    if (!core.wall_limited) {
        for (uint32_t index = 0; index < core.leg_count; ++index) {
            core.legs[index].limited &= kLimitedBit;
        }
        return;
    }
    for (uint32_t index = 0; index < core.leg_count; ++index) {
        LegInfo &leg = core.legs[index];
        uint8_t *data = leg_data(core, leg);
        fade(data, leg.count, level);
        // A leg that the wall's fade took above its budget, which its own pass had brought
        // within it, by its own budget again.
        if (leg.budget != 0 && (leg.limited & kOverBit) == 0) {
            const uint32_t estimate = limits_estimate(limits_sum(data, leg.count), leg.count);
            if (estimate > leg.budget) {
                fade(data, leg.count, leg_level(core, leg, estimate));
                leg.limited = kLimitedBit;
            }
        }
        leg.limited &= kLimitedBit;
    }
}

}  // namespace odrig
