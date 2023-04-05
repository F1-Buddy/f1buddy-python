# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

## Changelog

Fixed WDC command to show emojis


## To-do
- [x] DRIVER: fix wikipedia api, currently using pymediawiki
- [ ] DRIVER: Implement images for driver command, using new method
- [x] DRIVER: Does not work if name is lowercase
- [x] DRIVER: Names with special accents can only be accessed if user inputs their special accents (e.g. Kimi Räikkönen)
- [ ] LAPTIME: create team_colors.py file for teamcolors for different years
- [x] SCHEDULE: FIX LINE 80, uses local timezones which are ahead of EST, doesn't update properly (ex: Saudi GP over, but saudi local time > est time --> still shows saudi as next)
- [x] SCHEDULE: Display time as 12 hour, possible timer to event? maybe another command (x days, y hours... until event)
- [x] SCHEDULE: Fix timezones for each race
- [ ] General: port everything else (...)
## Issues

1.  Next Command: Timezone is calculated using latitude and longitude calculated from city name of circuit location (lol)

    sometimes is inaccurate and doesnt always convert to EST/New York properly because of daylight savings (ik you got me jubayer)

2. Not sure if schedule accounts for daylight savings/works properly for *every* location

3. Currently no support for PreSeason Testing, add later

