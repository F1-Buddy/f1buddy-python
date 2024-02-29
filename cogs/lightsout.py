import asyncio
import random
import discord
import traceback
from discord import app_commands
from discord.ext import commands
import repeated.embed as em


async def lights(interaction):
    print(interaction)
        
class lightsoutgame(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('lightsoutgame cog loaded')

    @app_commands.command(name='lightsout', description='Wait for the lights and react the fastest!')
    async def schedule(self, interaction: discord.Interaction):
        try:
            # defer response
            await interaction.response.defer(thinking=True)     
            
            delay = random.randrange(0,600)
            delay = (delay/100.0)

            # :black_circle: 
            # :red_circle: 
            lights0 = ":black_circle: :black_circle: :black_circle: :black_circle: :black_circle:\n:black_circle: :black_circle: :black_circle: :black_circle: :black_circle:"
            lights1 = ":red_circle: :black_circle: :black_circle: :black_circle: :black_circle:\n:red_circle: :black_circle: :black_circle: :black_circle: :black_circle:"
            lights2 = ":red_circle: :red_circle: :black_circle: :black_circle: :black_circle:\n:red_circle: :red_circle: :black_circle: :black_circle: :black_circle:"
            lights3 = ":red_circle: :red_circle: :red_circle: :black_circle: :black_circle:\n:red_circle: :red_circle: :red_circle: :black_circle: :black_circle:"
            lights4 = ":red_circle: :red_circle: :red_circle: :red_circle: :black_circle:\n:red_circle: :red_circle: :red_circle: :red_circle: :black_circle:"
            lights5 = ":red_circle: :red_circle: :red_circle: :red_circle: :red_circle:\n:red_circle: :red_circle: :red_circle: :red_circle: :red_circle:"
            dc_embed = em.Embed(title="Lights out!",description=f"Wait for the lights and react the fastest!\n\n{lights0}")
            await interaction.followup.send(embed=dc_embed.embed)
            
            
            msg = await interaction.original_response()
            await msg.add_reaction("🏎️")
            
            await asyncio.sleep(1)
            dc_embed.embed.description = f"Wait for the lights and react the fastest!\n\n{lights1}"
            await interaction.edit_original_response(embed=dc_embed.embed)
            await asyncio.sleep(1)
            dc_embed.embed.description = f"Wait for the lights and react the fastest!\n\n{lights2}"
            await interaction.edit_original_response(embed=dc_embed.embed)
            await asyncio.sleep(1)
            dc_embed.embed.description = f"Wait for the lights and react the fastest!\n\n{lights3}"
            await interaction.edit_original_response(embed=dc_embed.embed)
            await asyncio.sleep(1)
            dc_embed.embed.description = f"Wait for the lights and react the fastest!\n\n{lights4}"
            await interaction.edit_original_response(embed=dc_embed.embed)
            await asyncio.sleep(1)
            dc_embed.embed.description = f"Wait for the lights and react the fastest!\n\n{lights5}"
            await interaction.edit_original_response(embed=dc_embed.embed)
            
            await asyncio.sleep(delay)
            dc_embed.embed.description = f"Wait for the lights and react the fastest!\n\n{lights0}"
            await interaction.edit_original_response(embed=dc_embed.embed)
            
            reaction, user = await self.bot.wait_for('reaction_add', check=lambda reaction, user: reaction.emoji == '🏎️')
            dc_embed.embed.title = "And away we go!"
            dc_embed.embed.description = f"{user.mention} got away the fastest!\n\n{lights0}"
            dc_embed.embed.set_footer(text=f"Lights held for {delay} seconds")  
                                        
            await interaction.edit_original_response(embed=dc_embed.embed)
        except Exception as e:
            print(e)
            traceback.print_stack()
        
        
async def setup(bot):
    await bot.add_cog(lightsoutgame(bot))