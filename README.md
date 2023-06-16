# f1buddy-python

A python version of the discordjs-f1-bot! 
Rewritten in python to use fastf1 since ergast goes down too often

Schedule             |  Standings|  Driver|  
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/schedule.png)  |  ![](/images/wdcwcc.png)|  ![](/images/driver.png)|  

Laptimes|  Results|  Positions
:-------------------------:|:-------------------------:|:-------------------------:
![](/images/laptimes.png)|  ![](/images/results.png)|  ![](/images/positions.png)

## Changelog

added legend to laptimes and fixed round input as a number not working

added positions command


## To-do
- [ ] (maybe) make round an optional input for laptime and positions
- [ ] use fastf1 ergast implementation for wdc and wcc
    - [ ] https://theoehrly.github.io/Fast-F1-Pre-Release-Documentation/ergast.html#fastf1.ergast.Ergast.get_driver_standings

## Issues

results, quali, wdc, and wcc are broken until ergast is fixed

wdc and wcc is due to ssl certificate

unsure of results and quali

