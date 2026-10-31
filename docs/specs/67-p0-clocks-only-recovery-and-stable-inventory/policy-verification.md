# Saved-policy verification

The actual native core was observed failing before the repair: injected first/partial
read failures and malformed settings emitted a normal frame at0ms; an open failure
also allowed normal playback. The UI regression displayed an ordinary no-clocks
reason instead of explaining unreadable settings. These were controlled host faults,
not a reproduction of the physical installation's spontaneous incident.

Regressions assert every produced frame remains black until policy is established,
bounded retry, unchanged committed bytes, normal default for genuinely missing files,
and explicit replacement with Only/Off/Between. Message-only writes are refused
while policy is unknown. A successful independent retry resumes the saved mode.

The existing host open contract distinguishes missing from error; read_at alone
does not. No new command, watchdog, pin, current or power setting is introduced.
Physical board/reset-cause and phone acceptance remain unperformed.

Discovered verification passed1085 core checks(1 skip),676 emulator checks(19 skips),
494 app checks and88 onboarding checks. Startup trace expectations include the new
authoritative probe. Measured Core3784 and drive arena131037 bytes remain under the
unchanged4096/131072 limits; compiler frame bound remains512. The documentation's
example/read-only memory totals were updated to match measurement as well.
