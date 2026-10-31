# Controlled local reproductions

[evidence.json](evidence.json) records the actual observed results and source hashes.
No real-board failure is claimed. The injected errors establish existing failure
paths; finding the exact trigger of the owner's spontaneous incident remains work.

- [reproduce-client.cjs](reproduce-client.cjs) executes unchanged production functions
  extracted from client.js in a small Node VM with controlled command replies. It
  observes Only entry, an empty lookup/recovery, the next identical Only status,
  and reconnect invalidation of otherwise unchanged known catalog keys.
- [reproduce-native.py](reproduce-native.py) runs the actual shared core through its
  native binding on a temporary installed show and clock card. The healthy case and
  a settings-read error use identical valid saved Only bytes. The faulty case
  selects Off and plays the internal root animation.

For replay, use a fresh owned worktree at the recorded inspected revision and copy
the scripts into its ignored working area. Build its matching native core first
using the repository's platform instructions; never load a DLL built from a
different core/host ABI. Run each script from that repository root. The native
script uses a fresh `build/seed67-native-lab`; retain the output as evidence. These
explicit diagnosis tools are not production changes or registered suite tests.

The original native DLL was built at74eb4ac; the core sources were unchanged at the
inspected d39bb35. Scripts close their host files; no physical board is opened,
flashed or reconfigured. Their output files stay under ignored `build/`.
