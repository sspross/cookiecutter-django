#!/bin/bash
set -e
#
# One-command local dev loop. Opens a tmux session laid out as:
#
#   +---------------------+-----------------+
#   |                     | make frontend.dev   (top)
#   |                     +-----------------+
#   |   shell (you /      | make backend.dev    (mid)
#   |   your agent here)  +-----------------+
#   |                     | make worker.dev     (bottom)
#   +---------------------+-----------------+
#
# The three right panes just call the standalone `make *.dev` targets, so
# there is a single source of truth for how each process starts. tmux is
# optional: without it, run those three targets in separate terminals
# (see the README).
#
SESSION="{{ cookiecutter.project_slug }}"

if ! command -v tmux >/dev/null 2>&1; then
	echo "make dev needs tmux (brew install tmux), or run make frontend.dev / make backend.dev / make worker.dev in separate terminals" >&2
	exit 1
fi

# Connect to whichever client we have: switch within tmux, attach from a
# plain shell.
connect() {
	if [ -n "$TMUX" ]; then
		exec tmux switch-client -t "$SESSION"
	else
		exec tmux attach-session -t "$SESSION"
	fi
}

# Re-running `make dev` reconnects to a running session — never rebuild or
# kill work in progress.
if tmux has-session -t "$SESSION" 2>/dev/null; then
	connect
fi

# Build the layout detached. Pane creation order makes the right column,
# top->bottom, panes 1, 3, 2 (same split sequence as a known-good setup).
tmux new-session -d -s "$SESSION" -n dev

# Mouse mode: scroll panes with the wheel, click to select, drag borders to
# resize. Scoped to this session so it never touches the user's tmux config.
tmux set-option -t "$SESSION" mouse on

tmux split-window -h -p 33 -t "$SESSION:0"
tmux split-window -v -t "$SESSION:0.1"
tmux split-window -v -t "$SESSION:0.1"

tmux send-keys -t "$SESSION:0.1" "make frontend.dev" C-m
tmux send-keys -t "$SESSION:0.3" "make backend.dev" C-m
tmux send-keys -t "$SESSION:0.2" "make worker.dev" C-m

# Land in the big left pane: a plain shell at the repo root. Start your
# editor or agent here yourself.
tmux select-pane -t "$SESSION:0.0"

connect
