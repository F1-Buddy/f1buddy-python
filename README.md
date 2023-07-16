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
- [ ] (maybe) make round an optional input for laptime and positions
- [ ] /avgpos will not generate a new graph after the race has occurred, if previously generated on same race weekend (e.g. generated on quali day, but will not update even after the race has occurred)
- [ ] align /laptimes to 0 on graph
- [x] add h2h, consistency, fastest_lap to /help
- [x] h2h - validate duplicate input (e.g. VER vs VER)
- [x] fastest_lap - 2020 season will not load, 2022 season rounds after 4 (imola) will not load
- [ ] general: move font and help images into lib 
- [ ] fix session.load for slower commands
- [ ] calling consistency more than once with the same args throws an error
## Issues

2020 season data is odd (example styrian gp, 2020 round 2)




