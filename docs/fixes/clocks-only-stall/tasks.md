# Urgent clocks-only stall

Seed64's seven task proofs remain intact. This is a separate owner-requested
diagnosis and repair, based on the same source as the currently delivered firmware.

- [x] 1. Prevent refresh-producer starvation under continuously overdue clock frames
  - Compile the actual firmware producer function in a portable scheduler fixture.
    Demonstrate the fault before changing production code: with32-ms rendering and
    an immediate consumer or queued notification, no idle opportunity exists for
    more than the five-second watchdog interval. Record the observed failure.
  - Ensure a real blocking tick outside the core lock after each poll; retain output
    ownership, notification gating, update/mapping suspension and watchdog settings.
  - Run the discovered firmware and emulator suites and actual shipped clocks in the
    native emulator; document evidence and the limits of desktop reproduction.
  - Commit the verified fix with this checkbox and the observed fail-first evidence.
  - Verified: two regression cases failed first with6400 ms uninterrupted work and
    zero blocking ticks, then passed after the fix. Full discovery passed654
    firmware cases(1 skip),671 emulator cases(19 skips),88 onboarding cases.
    Both accelerated native collection runs completed. Physical reset confirmation
    remains open; verification.md distinguishes the model from board evidence.

- [ ] 2. Build and deliver the urgent firmware fix
  - From the clean fix commit, build/inspect firmware through fw.py and publish
    verified bytes to the existing Drive file. Retain artifact/source/hash evidence.
  - Push the isolated fix commits to the existing delivery PR; validate its exact-head
    CI and notify.
    The unchanged APK needs no rebuild. Physical confirmation remains open.
