<a href="https://discord.com/api/oauth2/authorize?client_id=1059405703116242995&permissions=139586816064&scope=bot">
    <img src="/botPics/f1python192.png">
</a>

# f1buddy-python

A discord bot with all kinds F1 statistics and tools!
[Invite it to your server!](https://discord.com/api/oauth2/authorize?client_id=1059405703116242995&permissions=139586816064&scope=bot)

<a href="https://discord.com/api/oauth2/authorize?client_id=1059405703116242995&permissions=139586816064&scope=bot">
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
- added parameter to fiadoc
- fixed fiadoc wrong order of images
- added year input check function to wdc/wcc

## To-do
- [x] IMPORTANT fl is slightly broken, make it only use 1 embed for rounds completed < 10
- [x] create a input checking function in common
- [ ] convert following commands to new em.Embed: 
    - [x] `constructor_standings.py`
    - [ ] `driver.py`
    - [ ] `driver_standings.py`
    - [ ] `fiadoc.py`
    - [ ] `help.py`
    - [ ] `laptimes.py`
    - [ ] `positions.py`
    - [ ] `qualigap.py`
    - [ ] `speed.py`
    - [ ] `strategy.py`
- [ ] add year parameter to fiadoc
- [ ] create running changelog file
- [ ] fix outlier calculation for consistency, currently awful
- [ ] qualigap, laptimes, fl, and both standings commands are just bad. fix input checking to be less terrible
- [ ] speed is excessively long, convert to use embed class
- [ ] use newer folder structure instead of string for old commands like speed,laptimes,etc.
- [ ] fix outlier calculation for consistency

## Bugs
- [ ] IMPORTANT fl is completely broken, 2020 doesnt work
- [ ] /consistency ver 2018
