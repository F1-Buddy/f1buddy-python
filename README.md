<img src="/botPics/f1python192.png">

# f1buddy-python

A discord bot with all kinds F1 statistics and tools!
Invite it to your server!

<a href="https://discord.com/api/oauth2/authorize?client_id=1059405703116242995&permissions=2147798016&scope=bot">
    <img src="https://logodownload.org/wp-content/uploads/2017/11/discord-logo-01.png" width="79" height="56">
</a>

Preview a few of our commands below:

# Command Previews
<details><summary><b>General Commands</b></summary>
    
Schedule             |  Standings|  Driver|  
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/schedule.png)  |  ![](/images/wdcwcc.png)|  ![](/images/driver.png)|  

Race Results             |  Quali Results |  FIA Document|  
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/results.png)|    ![](/images/quali.png)|  ![](/images/fiadoc.png)|  

And more!!
</details>

<details><summary><b>Data/Telemetry Commands</b></summary>
    
Telemetry             |  Track Dominance |  Position Changes|  
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/telemetry.png)  |  ![](/images/trackdominance.png)|  ![](/images/positions.png)|  

Qualifying Gap             |  Laptime Consistency |  Laptimes |  
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/qualigap.png)|    ![](/images/consistency.png)|  ![](/images/laptimes.png)|  

And more!!
</details>


## Changelog
- cleaned up schedule code
- added new embeds to class


## To-do
- [ ] fix wdc hitting discord embed character limit. current implementation is hardcoded, just calculate and adjust as necessary
- [ ] IMPORTANT add telemetry option for just 1 driver and specific lap number (consider other commands)
- [ ] (should fix asap, easy) add error handling embed for consistency when can't find race (e.g. 2018)
- [ ] (should fix asap, easy) /avgpos will not generate a new graph after the race has occurred, if previously generated on same race weekend (e.g. generated on quali day, but will not update even after the race has occurred) 
- [ ] add error handling embed for consistency when can't find race (e.g. 2018)
- [ ] fix consistency bugging out when session occurs, but no data for session
- [ ] (low priority) (maybe) make round an optional input for laptime and positions
- [ ] (low priority) fix hardcoded removal of DEV vs RIC comparison in h2h & hardcoded position values for RIC in avgpos

## Bugs
- [ ] telemetry will bug out and display nothing or very weird outputs for a graph if called upon multiple times in quick succession
- [ ] fix consistency bugging out when session occurs, but no data for session
- [ ] if lap time data cannot be loaded from ergast (e.g. just after race results) for latest round, consistency will get stuck when calling 
without round/year args
- [ ] 2020 season data is odd (example styrian gp, 2020 round 2)
- [x] may need to call /fl a couple of times after first call to get output (seems to work just fine, cannot reproduce this bug)
- [x] calling consistency more than once with the same args throws an error (seems to work just fine, cannot reproduce this bug)