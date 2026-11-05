#!/bin/bash
set -e
SESSION="{{ cookiecutter.project_slug }}"

if ! command -v tmux >/dev/null 2>&1; then
	echo "make dev needs tmux (brew install tmux), or run make frontend.dev / make backend.dev / make worker.dev in separate terminals" >&2
	exit 1
fi

# tmux exits with "open terminal failed" when $TERM has no terminfo entry on this
# host, common for xterm-ghostty inside a container, VM or remote box.
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

if tmux has-session -t "$SESSION" 2>/dev/null; then
	connect
fi

tmux new-session -d -s "$SESSION" -n dev

tmux set-option -t "$SESSION" mouse on

tmux split-window -h -p 33 -t "$SESSION:0"
tmux split-window -v -t "$SESSION:0.1"
tmux split-window -v -t "$SESSION:0.1"

tmux send-keys -t "$SESSION:0.1" "make frontend.dev" C-m
tmux send-keys -t "$SESSION:0.3" "make backend.dev" C-m
tmux send-keys -t "$SESSION:0.2" "make worker.dev" C-m

tmux select-pane -t "$SESSION:0.0"

connect
