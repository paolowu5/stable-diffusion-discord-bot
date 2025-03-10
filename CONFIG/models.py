import discord
from discord.ui import Select, View
import aiohttp
from CONFIG.config import url, pfp, colour, red

async def models_command(interaction: discord.Interaction):
    # First get the currently loaded model
    current_model = "Unknown"
    
    async with aiohttp.ClientSession() as session:
        # Get the current Stable Diffusion options to find the current model
        async with session.get(url=f'{url}/sdapi/v1/options') as options_response:
            if options_response.status == 200:
                options_data = await options_response.json()
                current_model = options_data.get('sd_model_checkpoint', 'Unknown')
            else:
                # If we can't get the options, continue with the default value
                pass
                
        # Get the list of available models
        async with session.get(url=f'{url}/sdapi/v1/sd-models') as response:
            if response.status == 200:
                models_data = await response.json()
            else:
                embed = discord.Embed(
                    title="Error connecting to Stable Diffusion",
                    description="Unable to retrieve the model list. Verify that the API is active.",
                    color=red
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

    embed = discord.Embed(
        title="Stable Diffusion Models",
        description=f"**Currently loaded model:**\n`{current_model}`\n\nSelect the model you want to use for image generation.\n\nStable Diffusion offers different models with unique characteristics, each optimized for specific styles or image qualities.\n\nThe selected model will be used for all subsequent generations.",
        color=colour
    )
    embed.set_thumbnail(url=pfp)
    embed.set_footer(text="After selecting a model, it will take a few seconds to load it")

    options = []
    for i, model in enumerate(models_data):
        model_name = model["model_name"]
        display_name = model_name[:100] if len(model_name) > 100 else model_name
        # Set current model as default in the list
        is_default = (model_name == current_model)
        options.append(discord.SelectOption(
            label=display_name,
            value=model_name,
            default=is_default
        ))

    MAX_OPTIONS = 25
    dropdown_views = []
    
    for i in range(0, len(options), MAX_OPTIONS):
        select = Select(
            placeholder="Select a model",
            options=options[i:i+MAX_OPTIONS],
            custom_id=f"model_select_{i}"
        )
        
        async def model_callback(interaction, selected_model):
            payload = {"sd_model_checkpoint": selected_model}
            status_embed = discord.Embed(
                title="Loading model...",
                description=f"Loading model: **{selected_model}**\nPlease wait a moment.",
                color=colour
            )
            status_embed.set_thumbnail(url=pfp)
            await interaction.response.send_message(embed=status_embed)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url=f'{url}/sdapi/v1/options', json=payload) as response:
                    if response.status == 200:
                        success_embed = discord.Embed(
                            title="Model updated successfully",
                            description=f"The model **{selected_model}** has been loaded and will be used for all future generations.",
                            color=colour
                        )
                        success_embed.set_thumbnail(url=pfp)
                        await interaction.edit_original_response(embed=success_embed)
                    else:
                        error_data = await response.json()
                        error_embed = discord.Embed(
                            title="Error loading the model",
                            description=f"An error occurred while loading the model.\nError: {error_data.get('detail', 'Unknown error')}",
                            color=red
                        )
                        await interaction.edit_original_response(embed=error_embed)

        select.callback = lambda i, s=select: model_callback(i, s.values[0])
        view = View()
        view.add_item(select)
        dropdown_views.append(view)

    if dropdown_views:
        await interaction.response.send_message(embed=embed, view=dropdown_views[0])
        for view in dropdown_views[1:]:
            additional_embed = discord.Embed(
                title="Stable Diffusion Models (continued)",
                description="Other available models:",
                color=colour
            )
            await interaction.followup.send(embed=additional_embed, view=view)
    else:
        empty_embed = discord.Embed(
            title="No models found",
            description="No Stable Diffusion models were found. Verify that the models have been installed correctly.",
            color=red
        )
        await interaction.response.send_message(embed=empty_embed)