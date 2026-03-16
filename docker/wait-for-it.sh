#!/bin/bash
# wait-for-it.sh - Wait for a service to be available

set -e

host="$1"
shift
cmd="$@"

until curl -f "$host" > /dev/null 2>&1; do
  >&2 echo "Waiting for $host..."
  sleep 2
done

>&2 echo "$host is available - executing command"
exec $cmd