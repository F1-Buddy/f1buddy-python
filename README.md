# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## Changelog

Fixed schedule command
* Added local list of timezones in timezones.py to make command faster
* Moved old timezone calculation into a fallback function in case timezone not found in local list 


## To-do
- [x] Use distance to next/last session and display schedule for weekend with lower distance
    (for example if i use the command on saturday it should provide whole schedule for this weekend, not next week)
- [ ] Rewrite the schedule command timezone conversion
- [x] Fix the next command (fastf1 provides session start times in local time with no timezone information SEE ISSUES)
- [ ] port everything else (...)

## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)

    sometimes is inaccurate and doesnt always convert to EST/New York properly because of daylight savings (ik you got me jubayer)

2. Not sure if schedule accounts for daylight savings/works properly for *every* location

3. Currently no support for PreSeason Testing, add later