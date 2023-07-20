<img src="/botPics/f1python192.png">

# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1

Invite it to your server!

<a href="https://discord.com/api/oauth2/authorize?client_id=1059405703116242995&permissions=2147798016&scope=bot">
    <img src="https://logodownload.org/wp-content/uploads/2017/11/discord-logo-01.png" width="157" height="112">
</a>

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

run commands in executor, should work simultaneously now

moved sync out of laptimes

added a help command

added author to each embed


## To-do
- [ ] add predictions command
- [ ] (maybe) make round an optional input for laptime and positions
- [ ] /avgpos will not generate a new graph after the race has occurred, if previously generated on same race weekend (e.g. generated on quali day, but will not update even after the race has occurred)
- [ ] align /laptimes to 0 on graph
- [ ] fix session.load for slower commands (did not change yet for: qualigap, telemetry)
- [ ] calling consistency more than once with the same args throws an error
- [ ] may need to call /fl a couple of times after first call to get output
- [ ] telemetry will bug out and display nothing for a graph if called upon multiple times in quick succession
## Issues

2020 season data is odd (example styrian gp, 2020 round 2)




