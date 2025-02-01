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
import os

class KokoroTTSWorker:
    def __init__(self):
        self.process = None
        self.ready = asyncio.Event()
        self._start_task = None
        self.kokoro_venv_path = os.getenv("KOKORO_VENV_PATH")
        if not self.kokoro_venv_path:
            raise ValueError("KOKORO_VENV_PATH environment variable not set")
        
        self.python_executable = os.path.join(self.kokoro_venv_path, "Scripts", "python.exe")
        if not os.path.exists(self.python_executable):
            raise ValueError(f"Python executable not found at {self.python_executable}")
        
        # Lock for synchronized access to process streams
        self._stdin_lock = asyncio.Lock()
        self._stdout_lock = asyncio.Lock()

    async def ensure_worker_ready(self):
        if self.process is None:
            if self._start_task is None:
                self._start_task = asyncio.create_task(self._start_worker())
            await self._start_task
            await self.ready.wait()

    async def _start_worker(self):
        try:
            print("Starting TTS worker process...")
            self.process = await asyncio.create_subprocess_exec(
                self.python_executable,
                'kokoro_bridge.py',
                '--server',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            print("TTS worker process started")
            
            # Start the error logger
            asyncio.create_task(self._log_stderr())
            
            # Send ping message
            async with self._stdin_lock, self._stdout_lock:
                message = json.dumps({"type": "ping"})
                length_bytes = len(message).to_bytes(4, 'big')
                self.process.stdin.write(length_bytes)
                self.process.stdin.write(message.encode('utf-8'))
                await self.process.stdin.drain()
                
                # Wait for pong
                size_bytes = await self.process.stdout.read(4)
                if size_bytes:
                    self.ready.set()
                    print("TTS worker ready")
                else:
                    raise RuntimeError("Worker failed to respond to ping")
                
        except Exception as e:
            print(f"Failed to start TTS worker: {e}")
            if self.process:
                try:
                    self.process.terminate()
                    await self.process.wait()
                except:
                    pass
            self.process = None
            self.ready.clear()
            raise

    async def _log_stderr(self):
        """Log stderr output from the worker process"""
        while self.process and not self.process.stderr.at_eof():
            try:
                line = await self.process.stderr.readline()
                if line:
                    print(f"Worker stderr: {line.decode().strip()}")
                else:
                    break
            except Exception as e:
                print(f"Error reading stderr: {e}")
                break

    async def generate_audio(self, text):
        """Thread-safe audio generation with proper chunking"""
        try:
            await self.ensure_worker_ready()
            
            if self.process is None or self.process.stdin is None:
                raise RuntimeError("TTS worker is not running")
            
            async with self._stdin_lock, self._stdout_lock:
                # Send request
                message = json.dumps({"type": "generate", "text": text})
                length_bytes = len(message).to_bytes(4, 'big')
                self.process.stdin.write(length_bytes)
                self.process.stdin.write(message.encode('utf-8'))
                await self.process.stdin.drain()
                
                # Read full response size
                size_bytes = await self.process.stdout.read(4)
                if not size_bytes:
                    raise RuntimeError("Worker closed connection")
                
                total_size = int.from_bytes(size_bytes, 'big')
                print(f"Expecting {total_size} bytes of audio data")
                
                # Read all data
                audio_data = bytearray()
                remaining = total_size
                
                while remaining > 0:
                    chunk = await self.process.stdout.read(min(remaining, 32768))
                    if not chunk:
                        break
                    audio_data.extend(chunk)
                    remaining -= len(chunk)
                
                return bytes(audio_data)
                
        except Exception as e:
            print(f"Error generating audio: {e}")
            self.process = None
            self.ready.clear()
            raise


    async def shutdown(self):
        """Cleanly shut down the worker process"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                print(f"Error shutting down worker: {e}")
            finally:
                self.process = None
                self.ready.clear()