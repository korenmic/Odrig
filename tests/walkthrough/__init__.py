"""The suite that follows the pages for newcomers in a fresh copy of the repository.

It clones the repository into a temporary folder, sets the copy up as the getting-started
page says, and runs the commands of the page there. The setup installs three libraries of
Python and the packages of the converter from the network, all of them into the copy: its
`.venv` and its `converter/node_modules`. The programs that install them keep their caches
in the user's account, as they do for anybody who follows the page. It takes minutes, so it
is a suite of its own: no other test command starts it.
"""
