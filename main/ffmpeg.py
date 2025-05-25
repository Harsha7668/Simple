#ALL FILES UPLOADED - CREDITS 🌟 - @Sunrises_24
import subprocess
import zipfile
import asyncio
import ffmpeg
import os, sys

#ALL FILES UPLOADED - CREDITS 🌟 - @Sunrises_24

async def merge_videos_and_audios(input_file, output_file):
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", input_file,
        "-c", "copy",
        output_file
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg error: {stderr.decode()}")
        
