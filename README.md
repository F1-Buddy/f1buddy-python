# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## To-do

[ ] - Fix the next command (fastf1 provides session start times in local time with no timezone information SEE ISSUES)
[ ] - port everything else (...)

## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)
    sometimes is inaccurate and doesnt always convert to EST/New York properly (ik you got me jubayer)