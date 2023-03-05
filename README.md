# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## Changelog

Fixed WDC command to show emojis


## To-do
- [ ] DRIVER: fix wikipedia api, currently using pymediawiki
- [x] LAPTIME: rewrite laptime logic, currently uses 7 try/catch to catch errors, bad!
- [ ] LAPTIME: create team_colors.py file for teamcolors for different years
- [x] SCHEDULE: Display time as 12 hour, possible timer to event? maybe another command (x days, y hours... until event)
- [x] SCHEDULE: Use distance to next/last session and display schedule for weekend with lower distance
    (for example if i use the command on saturday it should provide whole schedule for this weekend, not next week)
- [ ] SCHEDULE: Rewrite the schedule command timezone conversion
- [x] SCHEDULE: Fix the next command (fastf1 provides session start times in local time with no timezone information SEE ISSUES)
- [ ] WCC: Add emojis to WCC similar to WDC, can use same map (move map into a separate file)
- [ ] WDC: Catch error where no emoji is available for constructor based on given year (Example: Renault 2018 = no emoji currently) (try except)
- [ ] WDC: Instead of looping over 20, loop over however many drivers are in a given season


- [ ] General: port everything else (...)
## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)

    sometimes is inaccurate and doesnt always convert to EST/New York properly because of daylight savings (ik you got me jubayer)

2. Not sure if schedule accounts for daylight savings/works properly for *every* location

3. Currently no support for PreSeason Testing, add later

