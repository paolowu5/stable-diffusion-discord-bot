import discord
import aiohttp
import datetime
import os
import re
import io
import base64
import uuid
import shutil
from PIL import Image
from CONFIG.config import negative_prompt, url, pfp

async def generate_image(prompt, nickname, day, width, height, steps, cfg, count):
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "cfg_scale": cfg,
        "sampler_index": "DPM++ 2M Karras",
        "batch_size": 4,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{url}/sdapi/v1/txt2img', json=payload) as response:
            data = await response.json()

    images = []
    for i in data['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
        images.append(image)
    grid_size = (2, 2)
    result_image = create_grid_image(images, grid_size)

    # Modified directory structure
    user_dir = os.path.join('output', 'txt2img', f"{nickname}", day)
    os.makedirs(user_dir, exist_ok=True)
    filename = re.sub(r'[^\w\-_\.]', '_', prompt)[:120]
    filename = f"{count}_{filename}.png"
    filepath = os.path.join(user_dir, filename)
    result_image.save(filepath)

    save_individual_images(prompt, images, user_dir, count)

    return filepath

async def upscale_image(interaction: discord.Interaction, image_index: int, prompt: str, count):
    colour = discord.Colour.from_str("0x11806a")
    nickname = interaction.user.name
    now = datetime.datetime.now()
    day = now.strftime("%d-%m-%Y")
    # Modified directory structure
    user_dir = os.path.join('output', 'txt2img', f"{nickname}", day)

    os.makedirs(user_dir, exist_ok=True)
    prompt = re.sub(r'[^\w\-_\.]', '_', prompt)[:120]
    individual_image_path_internal = os.path.join(user_dir, f"{count}_{prompt}{image_index}.png")
    pil_image = Image.open(individual_image_path_internal)
    
    embed = discord.Embed(
        title=f"Upscaling image {image_index}",
        description="Please wait...",
        color=colour
    )
    embed.set_thumbnail(url=pfp)
    await interaction.response.send_message(embed=embed)
    
    def pil_to_base64(pil_image):
        with io.BytesIO() as stream:
            pil_image.save(stream, "PNG", pnginfo=None)
            base64_str = str(base64.b64encode(stream.getvalue()), "utf-8")
            return "data:image/png;base64," + base64_str
    payload = {
        "image": pil_to_base64(pil_image),
        "upscaler_1": "ESRGAN_4x",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{url}/sdapi/v1/extra-single-image', json=payload) as response:
            data = await response.json()
    upscaled_image_data = data.get('image')

    if upscaled_image_data:
        upscaled_image = Image.open(io.BytesIO(base64.b64decode(upscaled_image_data)))
        upscaled_image_stream = io.BytesIO()
        upscaled_image.save(upscaled_image_stream, format='PNG')
        upscaled_image_stream.seek(0)
        channel = interaction.channel

        # Save upscaled image in the same folder with "_up" suffix
        upscaled_filename = f"{count}_{prompt}{image_index}_up.png"
        upscaled_filepath = os.path.join(user_dir, upscaled_filename)
        upscaled_image.save(upscaled_filepath)

        await interaction.delete_original_response()
        
        upscaled_msg = await channel.send(f"{interaction.user.mention} - {prompt}.png - Upscaled Image {image_index}", 
                                         file=discord.File(upscaled_image_stream, filename='upscaled_image.png'))

        await upscaled_msg.add_reaction("❤️")
        await upscaled_msg.add_reaction("👎")
    else:
        print("Upscaled image not found in the API response.")

def create_grid_image(images, grid_size):
    cell_width = max(image.width for image in images)
    cell_height = max(image.height for image in images)
    grid_width = cell_width * grid_size[1]
    grid_height = cell_height * grid_size[0]
    grid_image = Image.new('RGB', (grid_width, grid_height))
    for index, image in enumerate(images):
        x = cell_width * (index % grid_size[1])
        y = cell_height * (index // grid_size[1])
        grid_image.paste(image, (x, y))
    return grid_image

def save_individual_images(prompt, images, user_dir, count):
    for index, image in enumerate(images):
        filename = re.sub(r'[^\w\-_\.]', '_', prompt)[:120] + f"{index + 1}.png"
        filename = f"{count}_{filename}"
        filepath = os.path.join(user_dir, filename)
        image.save(filepath)

async def generate_variations(interaction, image_index, prompt, count, width, height, steps, cfg):
    """
    Generate 4 variations of an existing image using img2img.
    
    Args:
        interaction: Discord interaction
        image_index: Index of the image to vary (1-4)
        prompt: Original prompt
        count: Image counter
        width, height: Image dimensions
        steps, cfg: Generation parameters
    """
    colour = discord.Colour.from_str("0x11806a")
    red = discord.Colour.from_str("0xFF0000")
    
    embed = discord.Embed(
        title=f"Generating variations of image {image_index}",
        description=f"Please wait...",
        color=colour
    )
    embed.set_footer(text='it may take some time to process the variations')
    embed.set_thumbnail(url=pfp)
    await interaction.response.send_message(embed=embed)
    
    channel = interaction.channel
    nickname = interaction.user.name
    now = datetime.datetime.now()
    day = now.strftime("%d-%m-%Y")
    
    # Modified directory structure
    user_dir = os.path.join('output', 'txt2img', f"{nickname}", day)
    os.makedirs(user_dir, exist_ok=True)
    
    # Find original image
    clean_prompt = re.sub(r'[^\w\-_\.]', '_', prompt)[:120]
    individual_image_path = os.path.join(user_dir, f"{count}_{clean_prompt}{image_index}.png")
    
    if not os.path.exists(individual_image_path):
        error_embed = discord.Embed(
            title="Error",
            description=f"Could not find the original image to create variations.",
            color=red
        )
        await interaction.edit_original_response(embed=error_embed)
        return
    
    try:
        # Load image
        with open(individual_image_path, "rb") as image_file:
            image_data = image_file.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare payload for img2img
        payload = {
            "init_images": [f"data:image/png;base64,{encoded_image}"],
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "width": width,
            "height": height,
            "cfg_scale": cfg,
            "sampler_index": "DPM++ 2M Karras",
            "batch_size": 4,
            "denoising_strength": 0.75,  # Moderate value to retain part of the original image
        }
        
        # Send request to Stable Diffusion
        async with aiohttp.ClientSession() as session:
            async with session.post(url=f'{url}/sdapi/v1/img2img', json=payload) as response:
                if response.status != 200:
                    await interaction.edit_original_response(
                        embed=discord.Embed(title="Error generating variations", 
                                           description="Failed to connect to Stable Diffusion",
                                           color=red)
                    )
                    return
                data = await response.json()
        
        # Process received images
        images = []
        for i in data['images']:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
            images.append(image)
        
        # Create grid
        grid_size = (2, 2)
        variation_count = len(str(uuid.uuid4())[:8])  # Use unique ID
        result_image = create_grid_image(images, grid_size)
        
        # Save grid
        variations_dir = os.path.join(user_dir, "variations")
        os.makedirs(variations_dir, exist_ok=True)
        
        grid_filename = f"var_{image_index}_{variation_count}_{clean_prompt}.png"
        grid_filepath = os.path.join(variations_dir, grid_filename)
        result_image.save(grid_filepath)
        
        # Save individual images
        save_variation_images(images, variations_dir, variation_count, image_index, clean_prompt)
        
        # Create buttons for variations
        button1 = discord.ui.Button(label="U1", style=discord.ButtonStyle.primary)
        button2 = discord.ui.Button(label="U2", style=discord.ButtonStyle.primary)
        button3 = discord.ui.Button(label="U3", style=discord.ButtonStyle.primary)
        button4 = discord.ui.Button(label="U4", style=discord.ButtonStyle.primary)
        
        button_var1 = discord.ui.Button(label="V1", style=discord.ButtonStyle.success)
        button_var2 = discord.ui.Button(label="V2", style=discord.ButtonStyle.success)
        button_var3 = discord.ui.Button(label="V3", style=discord.ButtonStyle.success)
        button_var4 = discord.ui.Button(label="V4", style=discord.ButtonStyle.success)
        
        button_refresh = discord.ui.Button(style=discord.ButtonStyle.grey, emoji="🔄")
        
        # Callbacks for upscaling variations
        async def var_button1_callback(var_interaction):
            await upscale_variation(var_interaction, variation_index=1, prompt=prompt, 
                                  variation_count=variation_count, image_index=image_index)
            
        async def var_button2_callback(var_interaction):
            await upscale_variation(var_interaction, variation_index=2, prompt=prompt, 
                                  variation_count=variation_count, image_index=image_index)
            
        async def var_button3_callback(var_interaction):
            await upscale_variation(var_interaction, variation_index=3, prompt=prompt, 
                                  variation_count=variation_count, image_index=image_index)
            
        async def var_button4_callback(var_interaction):
            await upscale_variation(var_interaction, variation_index=4, prompt=prompt, 
                                  variation_count=variation_count, image_index=image_index)
        
        # Callbacks for variations of variations
        async def var_var_button1_callback(var_interaction):
            await generate_variations_of_variation(var_interaction, variation_index=1, prompt=prompt,
                                               variation_count=variation_count, original_index=image_index,
                                               width=width, height=height, steps=steps, cfg=cfg)
            
        async def var_var_button2_callback(var_interaction):
            await generate_variations_of_variation(var_interaction, variation_index=2, prompt=prompt,
                                               variation_count=variation_count, original_index=image_index,
                                               width=width, height=height, steps=steps, cfg=cfg)
            
        async def var_var_button3_callback(var_interaction):
            await generate_variations_of_variation(var_interaction, variation_index=3, prompt=prompt,
                                               variation_count=variation_count, original_index=image_index,
                                               width=width, height=height, steps=steps, cfg=cfg)
            
        async def var_var_button4_callback(var_interaction):
            await generate_variations_of_variation(var_interaction, variation_index=4, prompt=prompt,
                                               variation_count=variation_count, original_index=image_index,
                                               width=width, height=height, steps=steps, cfg=cfg)
        
        async def var_refresh_callback(var_interaction):
            await var_interaction.response.defer()
            await generate_variations(interaction, image_index, prompt, count, width, height, steps, cfg)
        
        button1.callback = var_button1_callback
        button2.callback = var_button2_callback
        button3.callback = var_button3_callback
        button4.callback = var_button4_callback
        
        button_var1.callback = var_var_button1_callback
        button_var2.callback = var_var_button2_callback
        button_var3.callback = var_var_button3_callback
        button_var4.callback = var_var_button4_callback
        
        button_refresh.callback = var_refresh_callback
        
        view = discord.ui.View()

        # First row: variation buttons + refresh
        view.add_item(button_var1)
        view.add_item(button_var2)
        view.add_item(button_var3)
        view.add_item(button_var4)
        view.add_item(button_refresh)
        # Second row: upscale buttons
        view.add_item(button1)
        view.add_item(button2)
        view.add_item(button3)
        view.add_item(button4)

        
        # Delete waiting message and send result
        await interaction.delete_original_response()
        
        result_message = f"{interaction.user.mention}: **Variations of Image {image_index}** (from `{prompt}`)"
        await channel.send(result_message, file=discord.File(grid_filepath), view=view)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Error generating variations",
            description=f"An error occurred: {str(e)}",
            color=red
        )
        await interaction.edit_original_response(embed=error_embed)
        print(f"Error generating variations: {e}")

def save_variation_images(images, variations_dir, variation_count, original_index, clean_prompt):
    """Save individual variation images."""
    for index, image in enumerate(images):
        filename = f"var_{original_index}_{variation_count}_{clean_prompt}_{index + 1}.png"
        filepath = os.path.join(variations_dir, filename)
        image.save(filepath)

async def upscale_variation(interaction, variation_index, prompt, variation_count, image_index):
    """Upscale a variation image."""
    colour = discord.Colour.from_str("0x11806a")
    nickname = interaction.user.name
    now = datetime.datetime.now()
    day = now.strftime("%d-%m-%Y")
    
    # Modified directory structure
    variations_dir = os.path.join('output', 'txt2img', f"{nickname}", day, "variations")
    clean_prompt = re.sub(r'[^\w\-_\.]', '_', prompt)[:120]
    variation_image_path = os.path.join(variations_dir, f"var_{image_index}_{variation_count}_{clean_prompt}_{variation_index}.png")
    
    embed = discord.Embed(
        title=f"Upscaling variation {variation_index}",
        description="Please wait...",
        color=colour
    )
    embed.set_thumbnail(url=pfp)
    
    await interaction.response.send_message(embed=embed)
    
    # Load image
    pil_image = Image.open(variation_image_path)
    
    # Upscale with same logic as upscale_image function
    def pil_to_base64(pil_image):
        with io.BytesIO() as stream:
            pil_image.save(stream, "PNG", pnginfo=None)
            base64_str = str(base64.b64encode(stream.getvalue()), "utf-8")
            return "data:image/png;base64," + base64_str
    
    payload = {
        "image": pil_to_base64(pil_image),
        "upscaler_1": "ESRGAN_4x",
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{url}/sdapi/v1/extra-single-image', json=payload) as response:
            data = await response.json()
    
    upscaled_image_data = data.get('image')
    
    if upscaled_image_data:
        upscaled_image = Image.open(io.BytesIO(base64.b64decode(upscaled_image_data)))
        upscaled_image_stream = io.BytesIO()
        upscaled_image.save(upscaled_image_stream, format='PNG')
        upscaled_image_stream.seek(0)
        
        channel = interaction.channel
        
        # Save upscaled image
        upscaled_filename = f"var_{image_index}_{variation_count}_{clean_prompt}_{variation_index}_up.png"
        upscaled_filepath = os.path.join(variations_dir, upscaled_filename)
        upscaled_image.save(upscaled_filepath)
        
        await interaction.delete_original_response()
        
        upscaled_msg = await channel.send(
            f"{interaction.user.mention} - Upscaled Variation {variation_index} (from `{prompt}`)", 
            file=discord.File(upscaled_image_stream, filename='upscaled_variation.png')
        )
        
        await upscaled_msg.add_reaction("❤️")
        await upscaled_msg.add_reaction("👎")
    else:
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="Error upscaling variation",
                description="Failed to upscale the image",
                color=discord.Colour.red()
            )
        )

async def generate_variations_of_variation(interaction, variation_index, prompt, variation_count, original_index, width, height, steps, cfg):
    """
    Generate variations of a variation (recursively).
    Similar to generate_variations but uses a variation image as input.
    """
    colour = discord.Colour.from_str("0x11806a")
    nickname = interaction.user.name
    now = datetime.datetime.now()
    day = now.strftime("%d-%m-%Y")
    
    embed = discord.Embed(
        title=f"Processing...",
        description=f"Getting variation image to create new variations",
        color=colour
    )
    embed.set_thumbnail(url=pfp)
    await interaction.response.send_message(embed=embed)
    
    # Modified directory structure
    clean_prompt = re.sub(r'[^\w\-_\.]', '_', prompt)[:120]
    variations_dir = os.path.join('output', 'txt2img', f"{nickname}", day, "variations")
    variation_source_path = os.path.join(variations_dir, f"var_{original_index}_{variation_count}_{clean_prompt}_{variation_index}.png")
    
    # Create temporary name for original image
    temp_dir = os.path.join('output', 'txt2img', f"{nickname}", day)
    os.makedirs(temp_dir, exist_ok=True)
    temp_image_path = os.path.join(temp_dir, f"temp_{clean_prompt}{original_index}.png")
    
    # Copy variation image to main folder for processing by generate_variations
    shutil.copy(variation_source_path, temp_image_path)
    
    # Modify count to point to new temporary image
    new_count = f"temp_{clean_prompt}"
    
    # Delete initial response message
    await interaction.delete_original_response()
    
    # Call generate_variations with new parameters
    await generate_variations(interaction, original_index, prompt, new_count, width, height, steps, cfg)