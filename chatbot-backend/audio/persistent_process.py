import asyncio
from fastapi import FastAPI, UploadFile, BackgroundTasks
import soundfile as sf
import numpy as np
from io import BytesIO
from nltk.tokenize import sent_tokenize
import multiprocessing
import json
from asyncio import Queue
import sys

class KokoroTTSWorker:
    def __init__(self):
        self.request_queue = Queue()
        self.process = None
        self.model = None
        self._start_worker()

    async def _start_worker(self):
        if self.process is None:
            # Create a subprocess that keeps the model loaded
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                'kokoro_bridge.py',
                '--server',  # New flag to indicate server mode
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Start the worker loop
            asyncio.create_task(self._worker_loop())

    async def _worker_loop(self):
        while True:
            try:
                # Read response size first (4 bytes for uint32)
                size_data = await self.process.stdout.read(4)
                if not size_data:
                    break
                
                size = int.from_bytes(size_data, 'big')
                # Then read the actual audio data
                audio_data = await self.process.stdout.read(size)
                
                # Put the result in the response queue
                await self.request_queue.put(audio_data)
            except Exception as e:
                print(f"Worker error: {e}")
                break

    async def generate_audio(self, text):
        # Send the text to the subprocess
        request = json.dumps({"text": text}) + "\n"
        self.process.stdin.write(request.encode())
        await self.process.stdin.drain()
        
        # Wait for the response
        return await self.request_queue.get()