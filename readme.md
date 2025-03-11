# Diffusion Bot

A powerful Discord bot that integrates with Stable Diffusion to generate and manipulate images.

<div align="left">
  <img src="https://i.postimg.cc/76644nJS/slim-imagine.jpg" alt="Diffusion Bot">
</div>

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Discord](https://img.shields.io/badge/Discord-Bot-7289DA?logo=discord)
![Stable Diffusion](https://img.shields.io/badge/Stable%20Diffusion-WebUI-orange)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Text-to-Image Generation

- Generate multiple images from text prompts using the `/imagine` command
- Customize aspect ratio, steps, and CFG scale to fine-tune your results
- Get a grid of 4 images with options to upscale or create variations

![example.png](https://i.postimg.cc/C5tYKnpd/example.png)

### Image-to-Image Transformation

- Transform existing images by uploading with a text prompt
- Applies ControlNet with LineArt for guided transformations
- No command needed - just upload and describe your desired transformation

![cubicle.png](https://i.postimg.cc/FszFymPh/cubicle.png)

### Model Management

- Switch between different Stable Diffusion models with the `/models` command
- View available models and the currently loaded model
- Seamlessly integrate with your local Stable Diffusion setup

![modelli.png](https://i.postimg.cc/rF7T5409/modelli.png)

### Customization

- Update negative prompts with the `/negative` command
- Set image resolution with the `/resolution` command
- Get example prompts with the `/prompt` command to inspire your creations

![HELP.png](https://i.postimg.cc/HWh1CM2C/HELP.png)

## Commands

| Command       | Description                                                   |
| ------------- | ------------------------------------------------------------- |
| `/imagine`    | Generate 4 images from a text prompt with optional parameters |
| `/models`     | View and select different Stable Diffusion models             |
| `/negative`   | View or update the negative prompt used in generation         |
| `/resolution` | Set the resolution for generated images                       |
| `/prompt`     | Get example prompts to inspire your creations                 |
| `/help`       | Display available commands and features                       |

## Installation

### Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Stable Diffusion WebUI running with API enabled

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/paolowu5/stable-diffusion-discord-bot.git
   cd stable-diffusion-discord-bot
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your settings in `CONFIG/config.py`:

   ```python
   TOKEN = "YOUR_DISCORD_BOT_TOKEN"
   url = "http://127.0.0.1:7860"
   ```

4. Locate your stable diffusion folder and edit webui-user.sh adding API in arguments, then run it:

   ```bash
   @echo off

    set PYTHON=
    set GIT=
    set VENV_DIR=
    set COMMANDLINE_ARGS=--api

    call webui.bat
   ```

5. Run the bot:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py` - Main bot initialization and command handling
- `config.py` - Configuration settings and prompt examples
- `image_generation.py` - Functions for text-to-image generation
- `img2img.py` - Functions for image-to-image transformation
- `models.py` - Model management functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">  
  <p>
    <a href="https://diffusionbot.pages.dev" target="_blank">Webpage</a> • 
    <a href="https://github.com/paolowu5/stable-diffusion-discord-bot/issues" target="_blank">Report Issues</a> • 
    <a href="https://github.com/AUTOMATIC1111/stable-diffusion-webui" target="_blank">Stable Diffusion WebUI</a>
  </p>
</div>
