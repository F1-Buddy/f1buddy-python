# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## Changelog

Disabled the bot connecting to discord in main.py to test out new schedule calculation method


## To-do
- [ ] Use distance to next/last session and display schedule for weekend with lower distance
    (for example if i use the command on saturday it should provide whole schedule for this weekend, not next week)
- [ ] Rewrite the schedule command timezone conversion
- [ ] Fix the next command (fastf1 provides session start times in local time with no timezone information SEE ISSUES)
- [ ] port everything else (...)

## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)

    sometimes is inaccurate and doesnt always convert to EST/New York properly because of daylight savings (ik you got me jubayer)