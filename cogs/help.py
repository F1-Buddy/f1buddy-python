import asyncio
import typing
import discord
from discord import app_commands
from discord.ext import commands
from lib.colors import colors
message_embed = discord.Embed(title=f"Help", description="Help") # boilerplate/initalization for global scope
is_real_command = False

def create_message_embed(command_name):
    try:
        help_string, is_real_command, filename = get_help_string(command_name)
        if is_real_command:
            message_embed = discord.Embed(title=f"f1buddy Help - {command_name}", description=help_string)
        else: 
            message_embed = discord.Embed(title="f1buddy Help", description=help_string)
        message_embed.set_author(name='f1buddy', icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        message_embed.colour = colors.default
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        file = discord.File(f"images/{filename}", filename=filename)
        message_embed.set_image(url=f'attachment://{filename}')
    except Exception as e:
        message_embed.description = f"Error Occured :( {e}"  
        print(e) 
    return message_embed, file        

def get_help_string(command_name):
    try:
        match command_name:
            case "null" | "help" | "/help":
                help_string = ""
                help_string += "If you are having any issues or want to provide feedback, please open a new issue on [GitHub](https://github.com/F1-Buddy/f1buddy-python/issues)\n\n"
                help_string += "Data from 2020 season can be a bit messy/buggy\n\n"
                help_string += "To see all commands and usage, type '/' and click on f1buddy as shown in the attached image\n"
                help_string += "If you need additional assistance, join the [f1buddy support server](https://discord.gg/Qx3gqWrpzJ)\n"
                filename = "help.png"
                is_real_command = False
            case "wdc" | "/wdc":
                print("match")
                help_string = "`/wdc` - Retrieves the current year's driver standings.\n\n"
                help_string += "This command retrieves the driver standings for the specified year in Formula 1.\n\n"
                help_string += "If a year is not provided, it will default to the current year.\n\n"
                help_string += "Arguments:\n- year (optional): The year for which you want to retrieve the driver standings.\n\n"
                help_string += "Examples:\n`/wdc` - Retrieves the current year's driver standings.\n\n"
                help_string += "`/wdc 2007` - Retrieves the driver standings for the year 2007."
                is_real_command = True
                filename = "wdc.png"
            case "wcc" | "/wcc":
                help_string = "`/wcc` - Retrieves the current year's constructor standings.\n\n"
                help_string += "`/wcc year` - Retrieves the constructor standings for the specified year.\n\n"
                help_string += "This command retrieves the constructor standings for the specified year in Formula 1.\n\n"
                help_string += "Arguments:\n- year (optional): The year for which you want to retrieve the constructor standings.\n\n"
                help_string += "Examples:\n`/wcc` - Retrieves the current year's constructor standings.\n"
                help_string += "`/wcc 2007` - Retrieves the constructor standings for the year 2007."
                is_real_command = True
                filename = "wcc.png"
            case "constructors" | "/constructors":
                help_string = "`/constructors` - Retrieves the current year's constructor information.\n\n"
                help_string += "`/constructors year` - Retrieves the constructor information for the specified year.\n\n"
                help_string += "`/constructors year round` - Retrieves the constructor information for the specified year and round.\n\n"
                help_string += "`/constructors round` - Retrieves the constructor information for the specified round of the current year.\n\n"
                help_string += "This command retrieves the constructor information for the specified year and round in Formula 1.\n\n"
                help_string += "Arguments:\n- year (optional): The year for which you want to retrieve the constructor information.\n"
                help_string += "- round (optional): The round number for which you want to retrieve the constructor information.\n\n"
                help_string += "Examples:\n`/constructors` - Retrieves the current year's constructor information.\n"
                help_string += "`/constructors 2015` - Retrieves the constructor information for the year 2015.\n"
                help_string += "`/constructors 2015 5` - Retrieves the constructor information for the year 2015 and round 5."
                is_real_command = True
                filename = "constructors.png"
            case "driver" | "/driver":
                help_string = "`/driver` - Get driver info.\n\n"
                help_string += "This command retrieves information about a specific driver in Formula 1.\n\n"
                help_string += "Arguments:\n- driver: The full name of the driver.\n\n"
                help_string += "Examples:\n`/driver Lewis Hamilton` - Retrieves information about Lewis Hamilton.\n"
                help_string += "`/driver Max Verstappen` - Retrieves information about Max Verstappen."
                is_real_command = True
                filename = "driver.png"
            case "laptimes" | "/laptimes":
                help_string = "`/laptimes` - Compare laptimes of two drivers in a race (2018 onwards).\n\n"
                help_string += "This command allows you to compare the laptimes of two drivers in a race.\n\n"
                help_string += "Arguments:\n"
                help_string += "- driver1: 3 Letter Code for Driver 1.\n"
                help_string += "- driver2: 3 Letter Code for Driver 2.\n"
                help_string += "- round: Round name or number (Australia or 3).\n"
                help_string += "- year (optional): Year of the race.\n\n"
                help_string += "Notes:\n"
                help_string += "- Make sure to use two different drivers.\n\n"
                help_string += "Examples:\n"
                help_string += "`/laptimes HAM VER Australia`\n"
                help_string += "`/laptimes BOT RIC 3 2022`"
                is_real_command = True
                filename = "laptimes.png"
            case "positions" | "/positions":
                help_string = "`/positions` - See driver position changes over the race.\n\n"
                help_string += "This command allows you to visualize the position changes of drivers during a race.\n\n"
                help_string += "Arguments:\n- round: The name or number of the race (e.g., Australia or 3).\n"
                help_string += "- year (optional): The year of the race. If not provided, the current year is used.\n\n"
                help_string += "Note: The round can be either the name of the race or its number.\n\n"
                help_string += "Example:\n`/positions Australia` - Visualize position changes for the Australian Grand Prix.\n"
                help_string += "`/positions 4 2022` - Visualize position changes for the fourth round of the 2022 season."
                is_real_command = True
                filename = "positions.png"
            case "quali" | "/quali":
                help_string = "`/quali` - Get results of a specific qualifying session.\n\n"
                help_string += "This command retrieves the qualifying results for a specific year and round in Formula 1.\n\n"
                help_string += "If a year and round are not provided, it will default to the latest completed qualifying session.\n\n"
                help_string += "Arguments:\n- year (optional): The year for which you want to retrieve the qualifying results.\n"
                help_string += "- round (optional): The round name or number for which you want to retrieve the qualifying results.\n\n"
                help_string += "Examples:\n`/quali` - Retrieves the results of the latest completed qualifying session.\n"
                help_string += "`/quali 2023 Australia` - Retrieves the qualifying results for the 2023 Australian Grand Prix."
                is_real_command = True
                filename = "quali.png"
            case "qualigap" | "/qualigap":
                help_string = "`/qualigap` - See driver position changes over the race.\n\n"
                help_string += "This command generates a graph showing the qualifying gap to the leader for a given round and year in Formula 1.\n\n"
                help_string += "Arguments:\n- round: Round name or number (e.g., 'Australia' or '3').\n"
                help_string += "- year (optional): The year for which you want to generate the graph.\n\n"
                help_string += "Examples:\n`/qualigap Australia` - Generate the qualifying gap graph for the current year's Australian Grand Prix.\n"
                help_string += "`/qualigap 3 2022` - Generate the qualifying gap graph for the year 2022's third round."
                is_real_command = True
                filename = "qualigap.png"
            case "results" | "/results":
                help_string = "`/results` - Get results of a specific race.\n\n"
                help_string += "This command retrieves the results of a specific race in Formula 1.\n\n"
                help_string += "Arguments:\n- year (optional): The year of the race. If not provided, defaults to the current year.\n"
                help_string += "- round (optional): The round name or number of the race. If not provided, retrieves the latest completed race.\n\n"
                help_string += "Examples:\n`/results` - Get the results of the latest completed race.\n"
                help_string += "`/results 2022` - Get the results of all races in the year 2022.\n"
                help_string += "`/results Australia` - Get the results of the race named 'Australia'.\n"
                help_string += "`/results 2021 3` - Get the results of the race with the round number 3 in the year 2021."
                is_real_command = True
                filename = "results.png"
            case "schedule" | "/schedule":
                help_string = "`/schedule` - Get the next event schedule.\n\n"
                help_string += "This command retrieves the schedule for the next Formula 1 event.\n\n"
                help_string += "The schedule includes various sessions such as practice, qualifying, sprint, and race.\n\n"
                help_string += "Example:\n`/schedule` - Retrieves the schedule for the next Formula 1 event."
                is_real_command = True
                filename = "schedule.png"
            case "trackdominance" | "/trackdominance":
                help_string = "`/trackdominance` - See track dominance between drivers on their personal fastest laps.\n\n"
                help_string += "This command displays the track dominance between two drivers based on their personal fastest laps.\n\n"
                help_string += "Arguments:\n"
                help_string += "- `sessiontype`: Choose between Race or Qualifying.\n"
                help_string += "- `driver1`: 3-letter code for Driver 1.\n"
                help_string += "- `driver2`: 3-letter code for Driver 2.\n"
                help_string += "- `round`: Round name or number (Australia or 3).\n"
                help_string += "- `year` (optional): Year.\n\n"
                help_string += "Examples:\n"
                help_string += "`/trackdominance Qualifying HAM VER Australia` - See track dominance between Hamilton and Verstappen in Qualifying for the Australian Grand Prix.\n"
                help_string += "`/trackdominance Race BOT PER 5 2022` - See track dominance between Bottas and Perez in Race 5 of 2022.\n"
                is_real_command = True
                filename = "trackdominance.png"
            case "telemetry" | "/telemetry":
                help_string = "`/telemetry` - Display telemetry data for selected drivers.\n\n"
                help_string += "This command displays the speed, throttle, and brake graphs for the two chosen drivers on a plot/graph with information about their time deltas.\n\n"
                help_string += "Arguments:\n- driver1: Three-letter code of the first driver.\n- driver2: Three-letter code of the second driver.\n- round: Race round.\n- sessiontype: Session type.\n- year (optional): Race year. If not provided, it will default to the current year.\n\n"
                help_string += "Examples:\n`/telemetry VER HAM 6 Race 2022` - Telemetry of VER and HAM in race of round 6 for 2022.\n"
                help_string += "/telemetry VER HAM 6 Race` - Telemetry of VER and HAM in race of round 6 for the current year."
                is_real_command = True
                filename = "telemetry.png"
            case "avgpos" | "/avgpos":
                help_string = "`/avgpos` - Generate and display a bar plot of average finish positions.\n\n"
                help_string += "This command generates a bar plot showing the average finish positions of drivers in a specific session type.\n\n"
                help_string += "Arguments:\n- event: The type of session for which you want to calculate the average finish positions.\n\n"
                help_string += "Examples:\n`/avgpos Race` - Generate the average finish position bar plot for the race sessions.\n"
                help_string += "`/avgpos Qualifying` - Generate the average finish position bar plot for the qualifying sessions.\n"
                is_real_command = True
                filename = "avgpos.png"
            case "fiadoc" | "/fiadoc":
                help_string = "`/fiadoc` - Get the latest FIA Document.\n\n"
                help_string += "This command retrieves and displays the latest FIA Document related to the FIA Formula One World Championship.\n\n"
                help_string += "Examples:\n`/fiadoc` - Retrieve and display the latest FIA Document.\n"
                is_real_command = True
                filename = "fiadoc.png"
            case "strategy" | "/strategy":
                help_string = "`/strategy` - See tire strategies for a specific race.\n\n"
                help_string += "This command retrieves and displays the tire strategies used by drivers during a specific race.\n\n"
                help_string += "Arguments:\n- round: The name or number of the race.\n- year (optional): The year of the race. If not provided, it will default to the current year.\n\n"
                help_string += "Examples:\n`/strategy Australia` - Retrieve and display the tire strategies for the Australian race in the current year.\n"
                help_string += "`/strategy 3 2022` - Retrieve and display the tire strategies for the race with the round number 3 in the year 2022.\n"
                is_real_command = True
                filename = "strategy.png"
            case "consistency" | "/consistency":
                help_string = "`/consistency` - Plot driver laptime consistency\n\n"
                help_string += "This command plots and displays the laptime consistency of a driver during a specific race.\n\n"
                help_string += "Arguments:\n"
                help_string += "- `driver`: The three-letter code of the driver.\n"
                help_string += "- `round` (optional): The round name or number of the race. If not provided, it will default to the latest completed race.\n"
                help_string += "- `year` (optional): The year of the race. If not provided, it will default to the current year.\n\n"
                help_string += "Examples:\n"
                help_string += "`/consistency HAM` - Plot and display the laptime consistency of Lewis Hamilton for the latest completed race.\n"
                help_string += "`/consistency VER 3 2022` - Plot and display the laptime consistency of Max Verstappen for the race with round number 3 in the year 2022.\n"
                is_real_command = True
                filename = "consistency.png"
            case "h2h" | "/h2h":
                help_string = "`/h2h` - See head to head stats of specific drivers or teammate pairings. May take some time to load.\n\n"
                help_string += "This command displays the head-to-head stats between two drivers or teammate pairings in qualifying or race sessions.\n\n"
                help_string += "Arguments:\n"
                help_string += "- `driver1_code` (optional): The three-letter code of the first driver.\n"
                help_string += "- `driver2_code` (optional): The three-letter code of the second driver.\n"
                help_string += "- `event`: Choose between `Qualifying` or `Race`.\n\n"
                help_string += "Note: The `driver1_code` and `driver2_code` arguments are optional. If only one driver code is provided, it will compare the driver against all other drivers.\n\n"
                help_string += "Examples:\n"
                help_string += "`/h2h HAM VER Race` - Display head-to-head stats between Hamilton and Verstappen in race sessions.\n"
                help_string += "`/h2h ALO Qualifying` - Display head-to-head stats of Fernando Alonso against all other drivers in qualifying sessions.\n"
                help_string += "`/h2h Race - Display head-to-head stats of all drivers in race sessions.\n"
                is_real_command = True
                filename = "h2h.png"
            case "fl" | "/fl":
                help_string = "`/fl` - Get fastest lap\n\n"
                help_string += "This command retrieves and displays the fastest lap information for a specific race or all races in a year.\n\n"
                help_string += "Arguments:\n- `round` (optional): The round name or number of the race. If not provided, it will retrieve the fastest lap information for all races in the given year.\n"
                help_string += "- `year` (optional): The year of the race. If not provided, it will default to 2023.\n\n"
                help_string += "Examples:\n`/fl Australia` - Retrieve and display the fastest lap information for the Australian race in the default year (2023).\n"
                help_string += "`/fl 3 2022` - Retrieve and display the fastest lap information for the race with the round number 3 in the year 2022.\n"
                help_string += "`/fl` - Retrieve and display the fastest lap information for all races in the default year (2023).\n"
                is_real_command = True
                filename = "fl.png"
            case _:
                help_string = f"Command '{command_name}' not recognized. Please type the command name as it is verbatim in the bot's commands."
                is_real_command = False
                filename = "laeppa-vika-half-life-alyx.gif"
    except Exception as e:
        help_string = f"An error occurred while processing your request: {e}"
        is_real_command = False
        filename = "laeppa-vika-half-life-alyx.gif"
        print(f"Error: {e}")
        
    return help_string, is_real_command, filename
            
class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Help cog loaded')

    @app_commands.command(name='help', description='get help')
    async def help(self, interaction: discord.Interaction, command_name: typing.Optional[str]):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        if command_name is None:
            help_embed, file_embed = await loop.run_in_executor(None, create_message_embed, "null")
        else:
            command_name = command_name.lower()
            help_embed, file_embed = await loop.run_in_executor(None, create_message_embed, command_name)
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=help_embed, file=file_embed)
        except Exception as e:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=message_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(Help(bot))