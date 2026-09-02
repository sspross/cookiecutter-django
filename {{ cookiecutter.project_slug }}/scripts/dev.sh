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
# The three right panes call the standalone `make *.dev` targets, so there is
# one source of truth for how each process starts. tmux is optional: without
# it, run those three targets in separate terminals.
#
SESSION="{{ cookiecutter.project_slug }}"

if ! command -v tmux >/dev/null 2>&1; then
	echo "make dev needs tmux (brew install tmux), or run make frontend.dev / make backend.dev / make worker.dev in separate terminals" >&2
	exit 1
fi

# tmux refuses to start ("open terminal failed: missing or unsuitable terminal")
# when $TERM has no terminfo entry on this host — common when the terminal
# (e.g. Ghostty's xterm-ghostty) isn't installed inside a container / VM /
# remote box. Fall back to a universally-available description for this session.
if ! infocmp "$TERM" >/dev/null 2>&1; then
	echo "note: '$TERM' terminfo missing here; using xterm-256color for tmux" >&2
	export TERM=xterm-256color
fi

connect() {
	if [ -n "$TMUX" ]; then
		exec tmux switch-client -t "$SESSION"
	else
		exec tmux attach-session -t "$SESSION"
	fi
}

# Reconnect rather than rebuild: never kill work in progress.
if tmux has-session -t "$SESSION" 2>/dev/null; then
	connect
fi

# Built detached. The split order below numbers the right column, top to
# bottom, as panes 1, 3, 2 — hence the send-keys targets further down.
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

# Land in the big left pane: a plain shell at the repo root.
tmux select-pane -t "$SESSION:0.0"

connect
