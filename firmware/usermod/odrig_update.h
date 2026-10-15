// An update of the firmware over Wi-Fi, sent to WLED's page: on a board with no second
// firmware slot it is refused before anything is written, with a message that says why
// and what to do instead. On a board of WLED's layout, WLED's own update stays.
#pragma once

namespace OdrigUpdate {

// Registers the refusal when no slot is there that an update could write. Called in
// setup(), which WLED runs before it registers its own pages, so that the refusal is
// the handler the web server finds first.
void begin();

// Whether updates over Wi-Fi are refused, for WLED's information.
bool refusing();

}  // namespace OdrigUpdate
