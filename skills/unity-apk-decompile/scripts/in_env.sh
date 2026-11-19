#!/usr/bin/env bash
# Usage: bash in_env.sh <workdir> '<command>'
# Runs <command> in a fresh bash with the tool environment (tools-env.sh) and the paths of
# <workdir>/paths.env (W, SO, META) loaded, so a step never depends on the caller's shell.
if [ $# -ne 2 ]; then
  echo "usage: bash in_env.sh <workdir> '<command>'" >&2
  exit 2
fi
_WORKDIR=$1
_CMD=$2
_HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$_HERE/tools-env.sh" || exit $?
W=$_WORKDIR
SO=
META=
if [ -f "$_WORKDIR/paths.env" ]; then
  source "$_WORKDIR/paths.env"
fi
export W SO META SK
exec bash -c "$_CMD"
