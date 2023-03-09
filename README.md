# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## Changelog

Fixed WDC command to show emojis


## To-do
- [ ] DRIVER: fix wikipedia api, currently using pymediawiki
- [ ] LAPTIME: create team_colors.py file for teamcolors for different years
- [x] SCHEDULE: Display time as 12 hour, possible timer to event? maybe another command (x days, y hours... until event)
- [ ] SCHEDULE: Fix timezones for each race
- [ ] General: port everything else (...)
## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)

    sometimes is inaccurate and doesnt always convert to EST/New York properly because of daylight savings (ik you got me jubayer)

2. Not sure if schedule accounts for daylight savings/works properly for *every* location

3. Currently no support for PreSeason Testing, add later

