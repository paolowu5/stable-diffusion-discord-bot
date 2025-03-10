import discord
from discord.ui import Button, View, Select
from discord import app_commands
from discord.ext import commands
from discord.interactions import Interaction
import datetime
import random
import pyperclip

from CONFIG.config import TOKEN, negative_prompt, prompt_examples, url, pfp, colour, red
from CONFIG.image_generation import generate_image, upscale_image, create_grid_image, save_individual_images, generate_variations
from CONFIG.img2img import process_img2img, process_img2img_command
from CONFIG.models import models_command


count = 0
count_img2img = 0

bot = commands.Bot(command_prefix="+++", intents=discord.Intents.all())

# Classes
class MyBot(discord.Client):
    resolution_values = {
        "width": 512,
        "height": 512,
    }

class NegativeModal(discord.ui.Modal, title="New negative prompt"):
    message = discord.ui.TextInput(style=discord.TextStyle.long, label="New Negative Prompt", required=True, placeholder="past your new negative prompt here")
    async def on_submit(self, interaction: Interaction):
        new_negative_prompt = self.message.value
        global negative_prompt
        negative_prompt = new_negative_prompt
        embed = discord.Embed(title='*UPDATED* - Negative prompt', description=negative_prompt, color=colour)
        embed.set_thumbnail(url=pfp)
        button_new = Button(label="NEW NEGATIVE PROMPT", style=discord.ButtonStyle.danger)
        async def button_new_callback(interaction):
            negative_modal = NegativeModal()
            await interaction.response.send_modal(negative_modal)
        view = View()
        view.add_item(button_new)
        button_new.callback = button_new_callback
        await interaction.response.send_message(embed=embed, view=view)
        return

# Help menu
async def prompt(interaction):
    random_index = random.randint(0, len(prompt_examples) - 1)
    random_prompt = prompt_examples[random_index]
    embed = discord.Embed(
            title='TRY THIS PROMPT',
            description=random_prompt,
            color=colour
        )
    embed.set_thumbnail(url=pfp)
    embed.set_footer(text='For additional fascinating prompts, you can explore civitai.com', icon_url="https://images.crunchbase.com/image/upload/c_lpad,h_170,w_170,f_auto,b_white,q_auto:eco,dpr_1/gtxrcmtsvpjjevozblfa")
    
    button_prompt = Button(label="NEW PROMPT", style=discord.ButtonStyle.primary)
    button_copy = Button(label="COPY PROMPT", style=discord.ButtonStyle.green)

    async def button_prompt_callback(interaction):
        await prompt(interaction)
    async def button_copy_callback(interaction):
        pyperclip.copy(random_prompt)
        embed = discord.Embed(title='COPIED TO CLIPBOARD', description="", color=colour)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    button_prompt.callback = button_prompt_callback
    button_copy.callback = button_copy_callback

    view = View()
    view.add_item(button_prompt)
    view.add_item(button_copy)
    await interaction.response.send_message(embed=embed, view=view)
   
async def negative(interaction):
    global negative_prompt
    embed = discord.Embed(title='Negative Prompt', description=negative_prompt, color=colour)
    embed.set_thumbnail(url=pfp)

    button_new = Button(label="NEW NEGATIVE PROMPT", style=discord.ButtonStyle.danger)

    async def button_new_callback(interaction):
        negative_modal = NegativeModal()
        await interaction.response.send_modal(negative_modal)
     
    view = View()
    view.add_item(button_new)
    button_new.callback = button_new_callback
    await interaction.response.send_message(embed=embed, view=view)

async def imagine_help(interaction):
    embed = discord.Embed(title='',description="With `Diffusion Bot` you can generate any image you want by providing a prompt or uploading an image",color=colour)
    embed.add_field(name='**Additional parameters**', value='Besides the *prompt*, you can input various parameters:\n\n`ASPECT` the aspect ratio of the images\n*default is 1:1 (square), try 16:9 (cinematic) or 7:10 (B5, print format)*\n\n`STEPS` detail phases of diffusion process\n*default is 25, higher number equals more detailed images (and more time to generate)*\n\n`CFG` details for scale value of generated image\n*default is 5, higher value means more fidelity to the text prompt provided*\n‎', inline=False)
    embed.set_footer(text='Use the /imagine command now and have fun!')
    embed.set_thumbnail(url=pfp)
    await interaction.response.send_message(embed=embed)

async def resolution(interaction):
    select = Select(placeholder="Choose the Resolution",
        options=[        
        discord.SelectOption(label="512x512px", value="512", default=True),
        discord.SelectOption(label="768x768px", value="768"),
        discord.SelectOption(label="1024x1024px", value="1024")],
        )    
    async def resolution_callback(interaction, select):
        res = select.values[0]
        width, height = int(res), int(res)
        MyBot.resolution_values["width"] = width
        MyBot.resolution_values["height"] = height

        embed = discord.Embed(
        title=f"{select.values[0]}x{select.values[0]}",
        description='resolution updated correctly',
        color=colour
    )
        await interaction.response.send_message(embed=embed)
        embed.set_thumbnail(url=pfp)
    select.callback = lambda i, s=select: resolution_callback(i, s)
    view = View()
    view.add_item(select)
    embed = discord.Embed(title=f"Set the Resolution", description='keep in mind that higher resolution equals more time to generate an image', color=colour)
    embed.set_thumbnail(url=pfp)
    await interaction.response.send_message(embed=embed, view=view)

# Events
@bot.event
async def on_ready():
    now = datetime.datetime.now()
    clock = now.strftime("%H:%M:%S")
    day = now.strftime("%d/%m/%Y")
    activity = discord.Activity(name="/help", type=discord.ActivityType.watching)
    await bot.change_presence(activity=activity, status=discord.Status.idle)

    print(f"\n[{day} {clock}] {bot.user} is alive")
    try:
        synched = await bot.tree.sync()
        print(f"Synched {len(synched)} command(s)")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message, steps: str = 14, denoising_strength: float = 0.5, cfg_scale: int = 7):
    await process_img2img(bot, message, steps, denoising_strength, cfg_scale)

# Commands
@bot.tree.command(name="prompt", description="View a random prompt ready to use")
async def prompt_command(interaction: discord.Interaction):
    await prompt(interaction=interaction)

@bot.tree.command(name="negative", description="View or update the negative prompt")
async def negative_command(interaction: discord.Interaction):
    await negative(interaction=interaction)

@bot.tree.command(name="help", description="Help menu")
async def help(interaction: discord.Interaction):

    button_imagine = Button(label="IMAGINE", style=discord.ButtonStyle.primary)
    button_resolution = Button(label="RESOLUTION", style=discord.ButtonStyle.primary)
    button_negative = Button(label="NEGATIVE", style=discord.ButtonStyle.primary)
    button_prompt = Button(label="PROMPT", style=discord.ButtonStyle.primary)
    button_models = Button(label="MODELS", style=discord.ButtonStyle.primary)
        
    async def button_imagine_callback(interaction):
        await imagine_help(interaction)
    async def button_prompt_callback(interaction):
        await prompt(interaction)
    async def button_resolution_callback(interaction):
        await resolution(interaction)
    async def button_negative_callback(interaction):
        await negative(interaction)
    async def button_models_callback(interaction):
        await models_command(interaction)
        
    button_imagine.callback = button_imagine_callback
    button_prompt.callback = button_prompt_callback
    button_resolution.callback = button_resolution_callback
    button_negative.callback = button_negative_callback
    button_models.callback = button_models_callback
    
    view = View()
    view.add_item(button_imagine)
    view.add_item(button_negative)
    view.add_item(button_resolution)
    view.add_item(button_prompt)
    view.add_item(button_models)

    embed = discord.Embed(title='',description="With `Diffusion Bot` you can generate any image you want by providing a prompt or uploading an image",color=colour)
    embed.add_field(name='‎', value='**COMMANDS**', inline=False)
    embed.add_field(name='', value="`/imagine`\n*Creates 4 images from a text prompt you provide*\n\n`/negative`\n*View or update the negative prompt*\n\n`/resolution`\n*Set the images' resolution*\n\n`/prompt`\n*Shows a random prompt ready to use*\n\n`/models`\n*Select which Stable Diffusion model to use*\n‎\n\n", inline=False)
    embed.add_field(name='**IMAGE TO IMAGE**', value='Simply upload an image to any channel with a text prompt in the same message. The bot will automatically transform your image based on the prompt you provide.\n‎', inline=False)
    embed.set_thumbnail(url=pfp)
        
    embed.set_footer(text='Try exploring the buttons below or use the command /imagine to generate a new image')
    await interaction.response.send_message(embed=embed, view=view)
@bot.tree.command(name="resolution", description="Set the image resolution")
async def resolution_command(interaction: discord.Interaction):
    await resolution(interaction=interaction)

@bot.tree.command(name="models", description="Select which Stable Diffusion model to use")
async def models_command_wrapper(interaction: discord.Interaction):
    await models_command(interaction)

@bot.tree.command(name="imagine", description="Generate new images")
@app_commands.describe(prompt="insert a prompt")
async def image(interaction: discord.Interaction, prompt: str, aspect: str = "1:1", steps: int = 25, cfg: int = 5):
    try:
        numerator, denominator = aspect.split(':')
        numerator = int(numerator)
        denominator = int(denominator)
        if denominator == 0:
            embed = discord.Embed(title=f"Can't divide a number by 0", description=f"*try 2:3 or 16:9*", color=red)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    except ValueError:
        embed = discord.Embed(title=f"Invalid aspect format. Please enter the aspect in the correct format.", description=f"*try 4:3 or 7:10*", color=red)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    aspect_result = numerator / denominator

    if steps < 2 or steps > 75:
        embed = discord.Embed(title=f"'steps' must be between 2 and 50", description=f"(default value is 25)", color=colour)
        embed.set_footer(text='keep in mind that higher resolution equals more time to generate an image')        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if cfg < 1 or cfg > 25:
        embed = discord.Embed(title=f"'cfg' must be between 1 and 25", description=f"(default value is 5)", color=colour)
        embed.set_footer(text='keep in mind that higher resolution equals more time to generate an image')
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    global count
    now = datetime.datetime.now()
    day = now.strftime("%d-%m-%Y")
    clock = now.strftime("%H:%M:%S")
    nickname = interaction.user.name
    server = interaction.guild
    channel = interaction.channel
    
    print(f"[{day} {clock}] [server: {server} \ channel: {channel}] - {nickname}: {prompt}")

    embed = discord.Embed(title=f"generating image, please wait...", description=f"{prompt}", color=colour)
    embed.set_footer(text='it may takes at least 1 minute to generate an image')
    
    await interaction.response.send_message(embed=embed)

    width = MyBot.resolution_values["width"]
    height = MyBot.resolution_values["height"]
    width = int(aspect_result * width)

    try:
        # Passa count corrente e usa lo stesso valore per griglia e immagini singole
        filepath = await generate_image(prompt, nickname, day, width, height, steps, cfg, count)
        # Incrementa count solo dopo aver generato e salvato tutto
        count += 1

        # Crea i pulsanti per upscale e variazioni
        button1 = Button(label="U1", style=discord.ButtonStyle.primary)
        button2 = Button(label="U2", style=discord.ButtonStyle.primary)
        button3 = Button(label="U3", style=discord.ButtonStyle.primary)
        button4 = Button(label="U4", style=discord.ButtonStyle.primary)
        
        button_var1 = Button(label="V1", style=discord.ButtonStyle.success)
        button_var2 = Button(label="V2", style=discord.ButtonStyle.success)
        button_var3 = Button(label="V3", style=discord.ButtonStyle.success)
        button_var4 = Button(label="V4", style=discord.ButtonStyle.success)
        
        button_refresh = Button(style=discord.ButtonStyle.grey, emoji="🔄")

        async def button_refresh_callback(interaction):
            embed = discord.Embed(title=f"Generating new set of images", description="", color=colour)
            embed.set_footer(text='You will receive a ping from the bot when complete')
            await interaction.response.send_message(embed=embed)
            filepath = await generate_image(prompt, nickname, day, width, height, steps, cfg, count)
            await interaction.delete_original_response()
            new_grid = await channel.send(f"{interaction.user.mention}: **{prompt}**", file=discord.File(filepath), view=view)
        
        async def button1_callback(interaction):
            await upscale_image(interaction, image_index=1, prompt=prompt, count=count - 1)

        async def button2_callback(interaction):
            await upscale_image(interaction, image_index=2, prompt=prompt, count=count - 1)

        async def button3_callback(interaction):
            await upscale_image(interaction, image_index=3, prompt=prompt, count=count - 1)

        async def button4_callback(interaction):
            await upscale_image(interaction, image_index=4, prompt=prompt, count=count - 1)
            
        # Callback per i pulsanti di variazione
        async def button_var1_callback(interaction):
            await generate_variations(interaction, image_index=1, prompt=prompt, count=count - 1, 
                                    width=width, height=height, steps=steps, cfg=cfg)
            
        async def button_var2_callback(interaction):
            await generate_variations(interaction, image_index=2, prompt=prompt, count=count - 1, 
                                    width=width, height=height, steps=steps, cfg=cfg)
            
        async def button_var3_callback(interaction):
            await generate_variations(interaction, image_index=3, prompt=prompt, count=count - 1, 
                                    width=width, height=height, steps=steps, cfg=cfg)
            
        async def button_var4_callback(interaction):
            await generate_variations(interaction, image_index=4, prompt=prompt, count=count - 1, 
                                    width=width, height=height, steps=steps, cfg=cfg)

        button_refresh.callback = button_refresh_callback
        button1.callback = button1_callback
        button2.callback = button2_callback
        button3.callback = button3_callback
        button4.callback = button4_callback
        button_var1.callback = button_var1_callback
        button_var2.callback = button_var2_callback
        button_var3.callback = button_var3_callback
        button_var4.callback = button_var4_callback
        
        view = View()
        # Prima riga: pulsanti di variazione + refresh
        view.add_item(button_var1)
        view.add_item(button_var2)
        view.add_item(button_var3)
        view.add_item(button_var4)
        view.add_item(button_refresh)
        # Seconda riga: pulsanti di upscale
        view.add_item(button1)
        view.add_item(button2)
        view.add_item(button3)
        view.add_item(button4)
        

        grid = await channel.send(f"{interaction.user.mention}: **{prompt}**\n*steps:* {steps} - *Cfg scale:* {cfg} - *resolution:* {width}x{height}px",
                                file=discord.File(filepath), view=view)
        
        grid_id = grid.id
        print(f"[{day} {clock}] [server: {server} \ channel: {channel}] - {nickname}: {prompt} = {filepath}")
        return
    
    except Exception as e:
        embed2 = discord.Embed(title='STABLE DIFFUSION IS OFF', description="error connectioin 404", colour=red)
        await interaction.edit_original_response(embed=embed2)


# Run the bot
bot.run(TOKEN)