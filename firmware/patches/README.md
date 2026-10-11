# Patches to WLED

A file here whose name ends in `.patch` is a change to a file of WLED 16.0.1, in the form
`git diff` writes. `python3 firmware/fw.py build` brings WLED's source in the work folder
back to the pinned commit and then applies every patch file with `git apply`, in the order
of the file names, so a name starts with a number: `010-what-it-changes.patch`. A patch that
does not apply stops the build with `patch-failed`.

WLED's source is not stored in this repository, so a patch file is the only place where a
change to one of WLED's own files can live. Each one says in its first lines what it changes
and why the usermod cannot do it from outside.

The folder holds no patch: the firmware needs no change to a file of WLED.
