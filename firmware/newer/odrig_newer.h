// Read first by every source of the trial build on the newer USB software: names the
// newer ESP-IDF changed, given back to the libraries that still use the old ones.
#pragma once

// NeoPixelBus 2.8.4 selects the GPIO function of a parallel output's pin with a call
// ESP-IDF 5.5 no longer has; the register macro does the same.
#define gpio_hal_iomux_func_sel(pin_reg, func) PIN_FUNC_SELECT(pin_reg, func)
