import discord
import aiohttp
import datetime
import os
import io
import base64
import requests
import asyncio
from PIL import Image, PngImagePlugin
from CONFIG.config import url, pfp, negative_prompt

# Define the global counter variable at the module level
count_img2img = 0

async def process_img2img_command(
    interaction: discord.Interaction,
    message,
    prompt: str,
    control_weight: float = 1.0,
    steps: int = 20,
    denoising_strength: float = 0.75,
    cfg_scale: float = 7.0
):
    global count_img2img
    channel = interaction.channel
    colour = discord.Colour.from_str("0x11806a")
    
    count_img2img += 1
    now = datetime.datetime.now()
    day = now.strftime("%d-%m-%Y")
    
    # Send processing message
    embed = discord.Embed(
        title=f"generating image, please wait...",
        description=f"{prompt}",
        color=colour
    )
    embed.set_footer(text='it may take some time to process the image')
    embed.set_thumbnail(url=pfp)
    waiting_message = await interaction.followup.send(embed=embed)
    
    for attachment in message.attachments:
        if attachment.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            author_nickname = interaction.user.display_name
            # Modified directory structure
            folder_path = os.path.join('output', 'img2img', f"{author_nickname}", day, "original")
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, attachment.filename)
            
            # First save the image
            await attachment.save(file_path)
            
            # Read the image and encode in base64 for ControlNet
            with open(file_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Updated payload for img2img with ControlNet matching web UI settings
            payload = {
                "init_images": [f"data:image/png;base64,{encoded_image}"],
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "sampler_name": "DPM++ 2M",
                "steps": 20,
                "denoising_strength": 0.75,
                "cfg_scale": 7,
                "width": 512,
                "height": 512,
                "batch_size": 1,
                "restore_faces": False,
                "seed": -1,
                "resize_mode": 1,  # 1 = Crop and resize
                "alwayson_scripts": {
                    "controlnet": {
                        "args": [
                            {
                                "enabled": True,
                                "module": "lineart",
                                "model": "control_v11p_sd15_lineart [43d4be0d]",
                                "weight": control_weight,
                                "image": f"data:image/png;base64,{encoded_image}",
                                "resize_mode": "Scale to Fit (Inner Fit)",
                                "processor_res": 512,
                                "threshold_a": 64,
                                "threshold_b": 64,
                                "pixel_perfect": True,
                                "control_mode": "Balanced",
                                "guidance_start": 0.0,
                                "guidance_end": 1.0,
                                "lowvram": False
                            }
                        ]
                    }
                }
            }

            try:
                # Send request to Stable Diffusion API
                async with aiohttp.ClientSession() as session:
                    async with session.post(url=f'{url}/sdapi/v1/img2img', json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            await interaction.followup.send(f"Error connecting to Stable Diffusion API. Status: {response.status}. Error: {error_text}", ephemeral=True)
                            return
                        data = await response.json()

                # Process the result
                for i in data['images']:
                    image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                    png_payload = {
                        "image": "data:image/png;base64," + i
                    }
                    response = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
                    pnginfo = PngImagePlugin.PngInfo()
                    pnginfo.add_text("parameters", response.json().get("info"))

                    # Modified directory structure
                    user_dir = os.path.join('output', 'img2img', f"{author_nickname}", day)
                    os.makedirs(user_dir, exist_ok=True)
                    file_base_name = os.path.splitext(attachment.filename)[0]
                    filename = f"{file_base_name}_cn_{count_img2img}.png"
                    filepath = os.path.join(user_dir, filename)
                    image.save(filepath, pnginfo=pnginfo)
                    
                    # Delete waiting message
                    await waiting_message.delete()
                    
                    # Send generated image with info embed
                    result_embed = discord.Embed(
                        title=f"Image Generated",
                        description=f"**Prompt:** {prompt}\n**Steps:** 20 - **Denoising:** 0.75 - **CFG Scale:** 7 - **Control Weight:** {control_weight}",
                        color=colour
                    )
                    result_embed.set_footer(text=f"{interaction.user.display_name}'s img2img generation")
                    result_embed.set_thumbnail(url=pfp)
                    
                    # Add reaction buttons
                    button_upscale = discord.ui.Button(label="Upscale", style=discord.ButtonStyle.primary)
                    button_regenerate = discord.ui.Button(label="Regenerate", style=discord.ButtonStyle.secondary)
                    
                    async def button_upscale_callback(interaction):
                        await interaction.response.defer()
                        # Implement upscaling logic here
                        upscale_embed = discord.Embed(
                            title="Upscaling image...",
                            description="Please wait while we enhance the image quality.",
                            color=colour
                        )
                        upscale_message = await interaction.followup.send(embed=upscale_embed)
                        
                        # Call upscaling API
                        def pil_to_base64(pil_image):
                            with io.BytesIO() as stream:
                                pil_image.save(stream, "PNG", pnginfo=None)
                                base64_str = str(base64.b64encode(stream.getvalue()), "utf-8")
                                return "data:image/png;base64," + base64_str
                                
                        upscale_payload = {
                            "image": pil_to_base64(image),
                            "upscaler_1": "ESRGAN_4x",
                            "upscaling_resize": 2  # 2x upscale
                        }
                        
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url=f'{url}/sdapi/v1/extra-single-image', json=upscale_payload) as response:
                                    if response.status != 200:
                                        await upscale_message.delete()
                                        await interaction.followup.send("Error connecting to upscaling API. Please try again later.", ephemeral=True)
                                        return
                                    upscale_data = await response.json()
                            
                            upscaled_image_data = upscale_data.get('image')
                            if upscaled_image_data:
                                upscaled_image = Image.open(io.BytesIO(base64.b64decode(upscaled_image_data)))
                                upscaled_image_stream = io.BytesIO()
                                upscaled_image.save(upscaled_image_stream, format='PNG')
                                upscaled_image_stream.seek(0)
                                
                                # Save upscaled image
                                upscaled_filename = f"{file_base_name}_cn_{count_img2img}_upscaled.png"
                                upscaled_filepath = os.path.join(user_dir, upscaled_filename)
                                upscaled_image.save(upscaled_filepath)
                                
                                await upscale_message.delete()
                                
                                upscale_result_embed = discord.Embed(
                                    title=f"Upscaled Image",
                                    description=f"**Original Prompt:** {prompt}",
                                    color=colour
                                )
                                upscale_result_embed.set_footer(text=f"{interaction.user.display_name}'s upscaled img2img")
                                
                                await channel.send(
                                    embed=upscale_result_embed, 
                                    file=discord.File(upscaled_image_stream, filename='upscaled_image.png')
                                )
                            else:
                                await upscale_message.delete()
                                await interaction.followup.send("Error processing upscaled image. Please try again.", ephemeral=True)
                        except Exception as e:
                            await upscale_message.delete()
                            await interaction.followup.send(f"Error during upscaling: {str(e)}", ephemeral=True)
                    
                    async def button_regenerate_callback(interaction):
                        await interaction.response.defer()
                        # Regenerate with same parameters
                        await process_img2img_command(
                            interaction, 
                            message, 
                            prompt, 
                            control_weight, 
                            steps, 
                            denoising_strength, 
                            cfg_scale
                        )
                    
                    button_upscale.callback = button_upscale_callback
                    button_regenerate.callback = button_regenerate_callback
                    
                    view = discord.ui.View()
                    view.add_item(button_upscale)
                    view.add_item(button_regenerate)
                    
                    await channel.send(embed=result_embed, file=discord.File(filepath), view=view)
                    
            except Exception as e:
                # Error handling
                print(f"Error in img2img: {e}")
                error_embed = discord.Embed(
                    title="Error",
                    description=f"An error occurred during image generation: {str(e)}",
                    color=discord.Colour.red()
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

# Updated function for handling message attachments
async def process_img2img(bot, message, steps: int = 20, denoising_strength: float = 0.75, cfg_scale: int = 7):
    global count_img2img
    channel_id = message.channel.id
    channel = bot.get_channel(channel_id)
    colour = discord.Colour.from_str("0x11806a")

    if message.author == bot.user:
        return
    
    # Only proceed if message has attachments
    if message.attachments:
        count_img2img += 1
        now = datetime.datetime.now()
        day = now.strftime("%d-%m-%Y")
        
        # If message has no text content, use a default prompt
        prompt = message.content if message.content else "image to image transformation"
        
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                author_nickname = message.author.display_name                
                # Modified directory structure
                folder_path = os.path.join('output', 'img2img', f"{author_nickname}", day, "original")
                os.makedirs(folder_path, exist_ok=True)
                file_path = os.path.join(folder_path, attachment.filename)
                
                # First save the image
                await attachment.save(file_path)
                
                # Now that the image is saved, we can safely delete the message
                await message.delete()
                
                # Send the embed message that the image is being generated
                embed = discord.Embed(
                    title=f"generating image, please wait...",
                    description=f"{prompt}",
                    color=colour
                )
                embed.set_footer(text='it may take some time to process the image')
                embed.set_thumbnail(url=pfp)
                waiting_message = await channel.send(embed=embed)

                # Read the image and encode in base64 for ControlNet
                with open(file_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

                # Updated payload to match web UI settings
                payload = {
                    "init_images": [f"data:image/png;base64,{encoded_image}"],
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "sampler_name": "DPM++ 2M",
                    "steps": 20,
                    "denoising_strength": 0.75,
                    "cfg_scale": 7,
                    "width": 512,
                    "height": 512,
                    "batch_size": 1,
                    "restore_faces": False,
                    "seed": -1,
                    "resize_mode": 1,  # 1 = Crop and resize
                    "alwayson_scripts": {
                        "controlnet": {
                            "args": [
                                {
                                    "enabled": True,
                                    "module": "lineart",
                                    "model": "control_v11p_sd15_lineart [43d4be0d]",
                                    "weight": 1.0,
                                    "image": f"data:image/png;base64,{encoded_image}",
                                    "resize_mode": "Scale to Fit (Inner Fit)",
                                    "processor_res": 512,
                                    "threshold_a": 64,
                                    "threshold_b": 64,
                                    "pixel_perfect": True,
                                    "control_mode": "Balanced",
                                    "guidance_start": 0.0,
                                    "guidance_end": 1.0,
                                    "lowvram": False
                                }
                            ]
                        }
                    }
                }

                try:
                    # Send request to Stable Diffusion API
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url=f'{url}/sdapi/v1/img2img', json=payload) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                error_embed = discord.Embed(
                                    title="Error",
                                    description=f"Failed to connect to Stable Diffusion. Status: {response.status}\n{error_text}",
                                    color=discord.Colour.red()
                                )
                                await waiting_message.edit(embed=error_embed)
                                return
                            data = await response.json()
                            
                    # Process the result
                    for i in data['images']:
                        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                        png_payload = {
                            "image": "data:image/png;base64," + i
                        }
                        response = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
                        pnginfo = PngImagePlugin.PngInfo()
                        pnginfo.add_text("parameters", response.json().get("info"))

                        # Save the generated image
                        user_dir = os.path.join('output', 'img2img', f"{author_nickname}", day)
                        os.makedirs(user_dir, exist_ok=True)
                        file_base_name = os.path.splitext(attachment.filename)[0]
                        filename = f"{file_base_name}_cn_{count_img2img}.png"
                        filepath = os.path.join(user_dir, filename)
                        image.save(filepath, pnginfo=pnginfo)
                        
                        # Delete the waiting embed
                        await waiting_message.delete()
                        
                        # Create buttons for upscaling and regeneration
                        button_upscale = discord.ui.Button(label="Upscale", style=discord.ButtonStyle.primary)
                        button_regenerate = discord.ui.Button(label="Regenerate", style=discord.ButtonStyle.secondary)
                        
                        async def button_upscale_callback(interaction):
                            await interaction.response.defer()
                            upscale_embed = discord.Embed(
                                title="Upscaling image...",
                                description="Please wait while we enhance the image quality.",
                                color=colour
                            )
                            upscale_message = await interaction.followup.send(embed=upscale_embed)
                            
                            # Call upscaling API
                            def pil_to_base64(pil_image):
                                with io.BytesIO() as stream:
                                    pil_image.save(stream, "PNG", pnginfo=None)
                                    base64_str = str(base64.b64encode(stream.getvalue()), "utf-8")
                                    return "data:image/png;base64," + base64_str
                                    
                            upscale_payload = {
                                "image": pil_to_base64(image),
                                "upscaler_1": "ESRGAN_4x",
                                "upscaling_resize": 2  # 2x upscale
                            }
                            
                            try:
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(url=f'{url}/sdapi/v1/extra-single-image', json=upscale_payload) as response:
                                        if response.status != 200:
                                            await upscale_message.delete()
                                            await interaction.followup.send("Error connecting to upscaling API. Please try again later.", ephemeral=True)
                                            return
                                        upscale_data = await response.json()
                                
                                upscaled_image_data = upscale_data.get('image')
                                if upscaled_image_data:
                                    upscaled_image = Image.open(io.BytesIO(base64.b64decode(upscaled_image_data)))
                                    upscaled_image_stream = io.BytesIO()
                                    upscaled_image.save(upscaled_image_stream, format='PNG')
                                    upscaled_image_stream.seek(0)
                                    
                                    # Save upscaled image
                                    upscaled_filename = f"{file_base_name}_cn_{count_img2img}_upscaled.png"
                                    upscaled_filepath = os.path.join(user_dir, upscaled_filename)
                                    upscaled_image.save(upscaled_filepath)
                                    
                                    await upscale_message.delete()
                                    
                                    upscale_result_embed = discord.Embed(
                                        title=f"Upscaled Image",
                                        description=f"**Original Prompt:** {prompt}",
                                        color=colour
                                    )
                                    upscale_result_embed.set_footer(text=f"{message.author.display_name}'s upscaled img2img")
                                    
                                    await channel.send(
                                        embed=upscale_result_embed, 
                                        file=discord.File(upscaled_image_stream, filename='upscaled_image.png')
                                    )
                                else:
                                    await upscale_message.delete()
                                    await interaction.followup.send("Error processing upscaled image. Please try again.", ephemeral=True)
                            except Exception as e:
                                await upscale_message.delete()
                                await interaction.followup.send(f"Error during upscaling: {str(e)}", ephemeral=True)
                        
                        async def button_regenerate_callback(interaction):
                            regenerate_embed = discord.Embed(
                                title=f"Regenerating image...",
                                description=f"{prompt}",
                                color=colour
                            )
                            regenerate_embed.set_footer(text='it may take some time to process the image')
                            regenerate_embed.set_thumbnail(url=pfp)
                            regen_message = await interaction.response.send_message(embed=regenerate_embed)
                            
                            try:
                                # Get original image again
                                with open(file_path, "rb") as image_file:
                                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                                
                                # Same payload as before
                                payload["init_images"] = [f"data:image/png;base64,{encoded_image}"]
                                
                                # Send request to Stable Diffusion API
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(url=f'{url}/sdapi/v1/img2img', json=payload) as response:
                                        if response.status != 200:
                                            await interaction.edit_original_response(
                                                embed=discord.Embed(
                                                    title="Error",
                                                    description=f"Failed to connect to Stable Diffusion. Status: {response.status}",
                                                    color=discord.Colour.red()
                                                )
                                            )
                                            return
                                        data = await response.json()
                                
                                # Process the new result
                                for i in data['images']:
                                    image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                                    png_payload = {
                                        "image": "data:image/png;base64," + i
                                    }
                                    response = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
                                    pnginfo = PngImagePlugin.PngInfo()
                                    pnginfo.add_text("parameters", response.json().get("info"))
                                    
                                    # Save the regenerated image
                                    count_img2img += 1
                                    new_filename = f"{file_base_name}_cn_{count_img2img}.png"
                                    new_filepath = os.path.join(user_dir, new_filename)
                                    image.save(new_filepath, pnginfo=pnginfo)
                                    
                                    # Delete regenerating message
                                    await interaction.delete_original_response()
                                    
                                    # Send the new image
                                    result_embed = discord.Embed(
                                        title=f"Regenerated Image",
                                        description=f"**Prompt:** {prompt}\n**Steps:** 20 - **Denoising:** 0.75 - **CFG Scale:** 7",
                                        color=colour
                                    )
                                    result_embed.set_footer(text=f"{message.author.display_name}'s img2img regeneration")
                                    result_embed.set_thumbnail(url=pfp)
                                    
                                    new_view = discord.ui.View()
                                    new_button_upscale = discord.ui.Button(label="Upscale", style=discord.ButtonStyle.primary)
                                    new_button_regenerate = discord.ui.Button(label="Regenerate", style=discord.ButtonStyle.secondary)
                                    
                                    new_button_upscale.callback = button_upscale_callback
                                    new_button_regenerate.callback = button_regenerate_callback
                                    
                                    new_view.add_item(new_button_upscale)
                                    new_view.add_item(new_button_regenerate)
                                    
                                    await channel.send(embed=result_embed, file=discord.File(new_filepath), view=new_view)
                            except Exception as e:
                                await interaction.edit_original_response(
                                    embed=discord.Embed(
                                        title="Error regenerating image",
                                        description=f"An error occurred: {str(e)}",
                                        color=discord.Colour.red()
                                    )
                                )
                        
                        button_upscale.callback = button_upscale_callback
                        button_regenerate.callback = button_regenerate_callback
                        
                        view = discord.ui.View()
                        view.add_item(button_upscale)
                        view.add_item(button_regenerate)
                        
                        # Send the generated image with an embed and buttons
                        result_embed = discord.Embed(
                            title=f"Image Generated",
                            description=f"**Prompt:** {prompt}\n**Steps:** 20 - **Denoising:** 0.75 - **CFG Scale:** 7",
                            color=colour
                        )
                        result_embed.set_footer(text=f"{message.author.display_name}'s img2img generation")
                        result_embed.set_thumbnail(url=pfp)
                        
                        await channel.send(embed=result_embed, file=discord.File(filepath), view=view)
                except Exception as e:
                    error_msg = f"Error in img2img: {str(e)}"
                    print(error_msg)
                    error_embed = discord.Embed(
                        title="Error",
                        description=error_msg,
                        color=discord.Colour.red()
                    )
                    await waiting_message.edit(embed=error_embed)