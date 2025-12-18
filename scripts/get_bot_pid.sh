#!/bin/bash
# Get health-agent bot PID by checking working directory

for pid in $(pgrep -f "python.*src\.main"); do
    cwd=$(pwdx $pid 2>/dev/null | cut -d' ' -f2)
    if [[ "$cwd" == *"health-agent"* ]]; then
        echo $pid
        exit 0
    fi
done

exit 1
