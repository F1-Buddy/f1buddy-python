# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## Changelog

Updated laptime 
* takes optional year argument
* tell user when given inputs are invalid


## To-do
- [ ] DRIVER: fix wikipedia api, currently using pymediawiki
- [x] LAPTIME: rewrite laptime logic, currently uses 7 try/catch to catch errors, bad!
- [ ] LAPTIME: create team_colors.py file for teamcolors for different years
- [x] SCHEDULE: Display time as 12 hour, possible timer to event? maybe another command (x days, y hours... until event)
- [x] SCHEDULE: Use distance to next/last session and display schedule for weekend with lower distance
    (for example if i use the command on saturday it should provide whole schedule for this weekend, not next week)
- [ ] SCHEDULE: Rewrite the schedule command timezone conversion
- [x] SCHEDULE: Fix the next command (fastf1 provides session start times in local time with no timezone information SEE ISSUES)
- [ ] General: port everything else (...)

## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)

    sometimes is inaccurate and doesnt always convert to EST/New York properly because of daylight savings (ik you got me jubayer)

2. Not sure if schedule accounts for daylight savings/works properly for *every* location

3. Currently no support for PreSeason Testing, add later

