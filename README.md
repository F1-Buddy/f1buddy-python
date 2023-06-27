<img src="/botPics/f1python192.png">

# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1

Invite it to your server!

<a href="https://discord.com/api/oauth2/authorize?client_id=1059405703116242995&permissions=2147798016&scope=bot">
    <img src="https://logodownload.org/wp-content/uploads/2017/11/discord-logo-01.png" width="157" height="112">
</a>



Schedule             |  Standings|  Driver|  
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/schedule.png)  |  ![](/images/wdcwcc.png)|  ![](/images/driver.png)|  

Laptimes|  Results|  Positions
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/laptimes.png)|  ![](/images/results.png)|  ![](/images/positions.png)

## Changelog

run commands in executor, should work simultaneously now

moved sync out of laptimes

added a help command

added author to each embed


## To-do
- [ ] add predictions command
- [ ] add str arg to help command to provide command-specific help
- [ ] (maybe) make round an optional input for laptime and positions
- [x] use fastf1 ergast implementation for wdc and wcc
    - [x] https://theoehrly.github.io/Fast-F1-Pre-Release-Documentation/ergast.html#fastf1.ergast.Ergast.get_driver_standings

## Issues

2020 season data is odd (exacmple styrian gp, 2020 round 2)




