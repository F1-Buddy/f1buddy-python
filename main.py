import fastf1
from fastf1 import plotting
from matplotlib import pyplot as plt


fastf1.Cache.enable_cache('cache/')
plotting.setup_mpl()

race = fastf1.get_session(2020, 'Turkish Grand Prix', 'R')
race.load()

mag = race.laps.pick_driver('MAG')
ham = race.laps.pick_driver('HAM')

fig, ax = plt.subplots()
ax.plot(mag['LapNumber'], mag['LapTime'], color='white')
ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
ax.set_title("MAG vs HAM")
ax.set_xlabel("Lap Number")
ax.set_ylabel("Lap Time")
plt.show()