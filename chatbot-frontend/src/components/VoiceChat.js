import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from 'react-lottie';
import listeningAnimation from "./Animation.json";
import "./VoiceChat.css";
import { sendAudioToBackend } from '../services/speechApi';

const VoiceChat = ({ onSelectOption, sendAudioToBackend, setChatHistory }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState(''); // State to manage text content
  const [interruptMessage, setInterruptMessage] = useState(''); // State to manage interrupt message
  const mediaRecorderRef = useRef(null);
  const stopFlagRef = useRef(false);
  const userSpeakingRef = useRef(false); // Flag to track if the user has started speaking
  const silenceDetectionStartedRef = useRef(false); // Flag to track if silence detection has started
  const botAudioRef = useRef(null); // Reference to track bot's audio
  const audioContextRef = useRef(null); // Audio context reference
  const silenceTimeoutRef = useRef(null); // Reference to manage silence timeout

  useEffect(() => {
    startRecording();
  }, []);

  const startRecording = async () => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        // Request audio stream from the user's microphone
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

        // Create a new MediaRecorder instance to record the audio
        const mediaRecorder = new MediaRecorder(stream);

        // Define what happens when data is available (audio chunk is recorded)
        mediaRecorder.ondataavailable = handleDataAvailable;

        // Save the media recorder instance for later use
        mediaRecorderRef.current = mediaRecorder;

        // Start recording
        mediaRecorder.start();
        setStatusText('Listening...'); // Update status text to listening

        // Initialize audio context and analyser
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        audioContextRef.current = audioContext;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const volumeThreshold = 15; // Adjust this threshold as needed

        const detectSilence = () => {
          analyser.getByteFrequencyData(dataArray);
          const avgVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      
          if (avgVolume > volumeThreshold) {
            userSpeakingRef.current = true;
            silenceDetectionStartedRef.current = true;
      
            // Interrupt bot if playing
            if (botAudioRef.current && !botAudioRef.current.paused) { // Check if not paused
              botAudioRef.current.pause();
              botAudioRef.current.currentTime = 0;
              setStatusText('Listening...');
              setInterruptMessage('');
            }
      
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }
      
          if (silenceDetectionStartedRef.current && avgVolume <= volumeThreshold) {
            if (!stopFlagRef.current && silenceTimeoutRef.current === null) {
              silenceTimeoutRef.current = setTimeout(() => {
                if (silenceDetectionStartedRef.current) {
                  console.log("Silence detected, stopping recording...");
                  stopRecordingAndProcess();
                  silenceDetectionStartedRef.current = false;
                }
              }, 2000);
            }
          }
      
          requestAnimationFrame(detectSilence);
        };

        detectSilence(); // Start monitoring for silence

        // Update state to reflect that the recording has started
        setIsRecording(true);
        setStatusText('Listening...'); // Update status text to listening
      } catch (err) {
        console.error("Error accessing audio devices:", err);
        if (!stopFlagRef.current) {
          cleanup();
          setChatHistory((prev) => [
            ...prev,
            { type: "text", sender: "bot", content: "Error: Unable to access audio devices." },
          ]);
          onSelectOption('voiceHistory');
        }
      }
    }
  };

  const stopRecordingAndProcess = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setStatusText('Processing...'); // Update status text to processing
  };

  const handleStopButton = () => {
    cleanup();
    onSelectOption('stop');
  };

  const cleanup = () => {
    stopFlagRef.current = true;  // Set stop flag to prevent new recordings

    // Stop recording and clean up media recorder
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      mediaRecorderRef.current = null;
    }

    // Clean up audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop any ongoing bot audio
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }

    // Clear all timeouts and flags
    clearTimeout(silenceTimeoutRef.current);
    silenceTimeoutRef.current = null;
    userSpeakingRef.current = false;
    silenceDetectionStartedRef.current = false;

    // Reset states
    setIsRecording(false);
    setStatusText('Stopped');
    setInterruptMessage('');
  };

  const handleDataAvailable = async (event) => {
    if (stopFlagRef.current) return;
  
    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });
  
      if (audioBlob.size > 1000) {
        console.log("User audio recorded:", audioBlob);
        setChatHistory((prev) => [
          ...prev,
          { type: "audio", sender: "user", content: URL.createObjectURL(audioBlob) },
        ]);
  
        try {
          await sendAudioToConversationEndpoint(audioBlob); // Send to backend and play response
          startRecording(); // Restart recording after bot response
        } catch (error) {
          console.error("Error handling bot audio:", error);
          cleanup();
        }
      }
    }
  };
  
  
  
  

  const handleStop = () => {
    // Reset logic can go here if needed
  };

  async function sendAudioToConversationEndpoint(audioBlob) {
    try {
        const response = await sendAudioToBackend(audioBlob);

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Backend error: ${response.status} - ${errorText}`);
            setChatHistory((prev) => [
                ...prev,
                { type: "text", sender: "bot", content: `Error: ${errorText || response.statusText}` },
            ]);
            return; // Important: Stop further processing if the response is an error
        }

        const reader = response.body.getReader();
        let accumulatedData = new Uint8Array();
        let chunkCounter = 0;
        const playbackQueue = [];
        let isPlaying = false;

        const playNextChunk = () => {
            if (playbackQueue.length === 0) {
                isPlaying = false;
                botAudioRef.current = null; // Clear the ref when playback is finished
                return;
            }
            isPlaying = true;
            const audioBlob = playbackQueue.shift();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            botAudioRef.current = audio; // Assign the audio to the ref

            audio.play().catch(error => {
                console.error("Error playing audio chunk:", error);
                URL.revokeObjectURL(audioUrl);
                playNextChunk();
                botAudioRef.current = null; // Clear the ref in case of error
            });

            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                playNextChunk();
            };
        };

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            if (value && value.byteLength > 0) {
                const combinedData = new Uint8Array(accumulatedData.length + value.length);
                combinedData.set(accumulatedData, 0);
                combinedData.set(value, accumulatedData.length);
                accumulatedData = combinedData;

                let startIndex = 0;
                while (startIndex < accumulatedData.length) {
                    const isWavHeader =
                        accumulatedData[startIndex] === 82 && // R
                        accumulatedData[startIndex + 1] === 73 && // I
                        accumulatedData[startIndex + 2] === 70 && // F
                        accumulatedData[startIndex + 3] === 70; // F

                    if (isWavHeader) {
                        let dataLength = accumulatedData.length - startIndex;
                        if (dataLength >= 8) { // Check for minimum RIFF header size
                            const riffChunkSize = new DataView(accumulatedData.buffer, startIndex + 4, 4).getUint32(0, true) + 8; // Read chunk size
                            if (dataLength >= riffChunkSize) {
                                const wavData = accumulatedData.subarray(startIndex, startIndex + riffChunkSize);
                                const chunkBlob = new Blob([wavData], { type: "audio/wav" });
                                playbackQueue.push(chunkBlob);
                                if (!isPlaying) playNextChunk();

                                startIndex += riffChunkSize;
                                continue; // Process next WAV in accumulated data
                            }
                        }
                    }
                    break; // No more complete WAV files found
                }
                accumulatedData = accumulatedData.subarray(startIndex); // Remove processed data
                console.log(`Chunk ${chunkCounter++}:`, { byteLength: value.byteLength });
            }
        }

        setChatHistory((prev) => [
            ...prev,
            { type: "text", sender: "bot", content: "Bot response..." }, // Add to history after successful processing
        ]);
        console.log("All audio chunks processed.");
    } catch (error) {
        console.error("Error streaming audio:", error);
        setChatHistory((prev) => [
            ...prev,
            { type: "text", sender: "bot", content: "Error processing bot response" },
        ]);
    }
}
  

  const defaultOptions = {
    loop: true,
    autoplay: true,
    animationData: listeningAnimation,
    rendererSettings: {
      preserveAspectRatio: "xMidYMid slice"
    }
  };

  return (
    <div className="voice-chat-container">
      <p className="status-text pulse">{statusText}</p> {/* Status text with pulse */}
      <p className="interrupt-text">{interruptMessage}</p> {/* Interrupt message */}
      <div className="listening-indicator">
        <Lottie 
          options={defaultOptions}
          height={300}
          width={300}
        />
      </div>
      <button className="stop-button" onClick={handleStopButton}>
        <X />
      </button>
    </div>
  );
};

export default VoiceChat;
