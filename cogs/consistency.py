import fastf1
from matplotlib import pyplot as plt, ticker
import pandas as pd
from lib.f1font import regular_font, bold_font
from lib.colors import colors

session = fastf1.get_session(2023, 1, 'R')
session.load(telemetry=True, laps=True)

specified_driver = 'VER'
driver_laps = session.laps[session.laps['Driver'] == specified_driver]
final_lap_number = driver_laps['LapNumber'].max()
mean_lap_time = driver_laps['LapTime'].mean().total_seconds()
std_lap_time = driver_laps['LapTime'].std()


fig, ax = plt.subplots(figsize=(9, 6))
# fig.set_facecolor('black')
# ax.set_facecolor('black')
ax.scatter(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), color='blue', label=specified_driver)
ax.axhline(mean_lap_time, color='red', linestyle='--', label='Mean Lap Time')
# ax.plot(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), color='blue', label=specified_driver)

y_ticks = ax.get_yticks()
converted_labels = []
for tick in y_ticks:
    minutes = int(tick // 60)
    seconds = int(tick % 60)
    converted_labels.append("{:02d}:{:02d}".format(minutes, seconds))

ax.set_yticklabels(converted_labels)
ax.set_title(f"{specified_driver} Laptime Consistency", fontproperties=bold_font)
ax.set_xlabel("Lap Number", fontproperties=regular_font, labelpad=10)
ax.set_ylabel("Lap Time", fontproperties=regular_font, labelpad=10)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(regular_font)
plt.rcParams['savefig.dpi'] = 300
plt.show()

# plt.savefig("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')
# plt.clf()
# plt.cla()
# plt.close()