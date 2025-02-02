import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from "react-lottie";
import listeningAnimation from "./Animation.json";
import "./Voice.css";
import { sendAudioToBackend } from "../services/speechApi";

import { useNavigate, useLocation } from "react-router-dom";

const VoiceChat = ({ onSelectOption, sendAudioToBackend, setChatHistory }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState(""); // State to manage text content
  const [interruptMessage, setInterruptMessage] = useState(""); // State to manage interrupt message
  const mediaRecorderRef = useRef(null);
  const stopFlagRef = useRef(false);
  const userSpeakingRef = useRef(false); // Flag to track if the user has started speaking
  const silenceDetectionStartedRef = useRef(false); // Flag to track if silence detection has started
  const botAudioRef = useRef(null); // Reference to track bot's audio
  const audioContextRef = useRef(null); // Audio context reference
  const silenceTimeoutRef = useRef(null); // Reference to manage silence timeout

  const isInterruptedRef = useRef(false);
  const isInterruptedRef_beta = useRef(false);

  const navigate = useNavigate();
  const location = useLocation();
  const isVoiceRoute = location.pathname === "/voice";

  const currentRequestId = useRef(0);
  const activeChunkProcessor = useRef(null);

 useEffect(() => {
        if (isVoiceRoute && !isRecording) {
            startRecording();
            setIsRecording(true);
        } else if (!isVoiceRoute && isRecording) {
            cleanup();
            setIsRecording(false);
        }
        return () => {
            if (isRecording) {
                cleanup();
            }
        };
    }, [isVoiceRoute, isRecording]);


    // Method to clear voice history
  const clearVoiceHistory = () => {
    // Clear localStorage
    localStorage.removeItem('voiceChatHistory');
    
    // If setChatHistory prop is provided, clear it
    if (setChatHistory) {
      setChatHistory([]);
    }
  };

  useEffect(() => {
    // Clear localStorage when the app is about to close
    const handleBeforeUnload = () => {
      clearVoiceHistory();
    };

    // Clear history when component mounts 
    clearVoiceHistory();
  
    // Add event listener when component mounts
    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('unload', handleBeforeUnload);
  
    // Clean up event listeners when component unmounts
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleBeforeUnload);
    };
  }, []);

  const startRecording = async () => {
    if (!isVoiceRoute || isRecording) return;
    
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        // Request audio stream from the user's microphone
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

        // Stop existing tracks before creating a new MediaRecorder
        if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
        if (audioContextRef.current) {
          audioContextRef.current.close();
        }

        // Create a new MediaRecorder instance to record the audio
        const mediaRecorder = new MediaRecorder(stream);

        // Define what happens when data is available (audio chunk is recorded)
        mediaRecorder.ondataavailable = handleDataAvailable;

        // Save the media recorder instance for later use
        mediaRecorderRef.current = mediaRecorder;

        // Start recording
        mediaRecorder.start();
        setStatusText("Listening..."); // Update status text to listening

        // Initialize audio context and analyser
        const audioContext = new (window.AudioContext ||
          window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        audioContextRef.current = audioContext;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const volumeThreshold = 40; // Adjust this threshold as needed

        const detectSilence = () => {
          analyser.getByteFrequencyData(dataArray);
          const avgVolume =
            dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

          if (avgVolume > volumeThreshold) {
            userSpeakingRef.current = true;
            silenceDetectionStartedRef.current = true;

            // Interrupt bot if playing
            if (botAudioRef.current && !botAudioRef.current.paused) {
              // Check if not paused
              botAudioRef.current.pause();
              botAudioRef.current.currentTime = 0;
              setStatusText('Stopped.'); // Display Stopped
              setInterruptMessage('');
              handleInterrupt()
            }
            

            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }

          if (
            silenceDetectionStartedRef.current &&
            avgVolume <= volumeThreshold
          ) {
            if (!stopFlagRef.current && silenceTimeoutRef.current === null) {
              silenceTimeoutRef.current = setTimeout(() => {
                if (silenceDetectionStartedRef.current) {
                  console.log("Silence detected, stopping recording...");
                  stopRecordingAndProcess();
                  silenceDetectionStartedRef.current = false;
                }
              }, 2000); //might go back to change this
            }
          }

          requestAnimationFrame(detectSilence);
        };

        detectSilence(); // Start monitoring for silence

        // Update state to reflect that the recording has started
        setIsRecording(true);
        setStatusText("Listening..."); // Update status text to listening
      } catch (err) {
        console.error("Error accessing audio devices:", err);
        if (!stopFlagRef.current) {
          cleanup();
          setChatHistory((prev) => [
            ...prev,
            {
              type: "text",
              sender: "bot",
              content: "Error: Unable to access audio devices.",
            },
          ]);
          onSelectOption("voiceHistory");
        }
      }
    }
  };

  const stopRecordingAndProcess = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setStatusText("Processing..."); // Update status text to processing
  };

  const handleStopButton = () => {
    cleanup();
    navigate("/voice-history");
  };

  const cleanup = () => {
    stopFlagRef.current = true;
    currentRequestId.current++;
  
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      mediaRecorderRef.current = null;
    }
  
    // Don't close audio context - just pause audio
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }
  
    // Clear timeouts
    clearTimeout(silenceTimeoutRef.current);
    silenceTimeoutRef.current = null;
  
    // Reset states
    setIsRecording(false);
    setStatusText("Stopped");
    setInterruptMessage("");
  };

  const handleDataAvailable = async (event) => {
    if (stopFlagRef.current || !userSpeakingRef.current) return;
  
    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });
  
      if (audioBlob.size > 1000) {
        console.log("User audio recorded:", audioBlob);
        setChatHistory((prev) => [
          ...prev,
          { type: "audio", sender: "user", content: URL.createObjectURL(audioBlob) },
        ]);
  
        try {
          await sendAudioToConversationEndpoint(audioBlob);
        } catch (error) {
          console.error("Error handling bot audio:", error);
          cleanup();
        }
      }
    }
  };

  const handleInterrupt = async () => {
    try {
      // Increment request ID to invalidate previous requests
      currentRequestId.current++;
      
      // Stop any ongoing audio immediately
      if (botAudioRef.current) {
        botAudioRef.current.pause();
        botAudioRef.current.currentTime = 0;
        botAudioRef.current = null;
      }
  
      // Cancel any ongoing chunk processing
      if (activeChunkProcessor.current) {
        activeChunkProcessor.current = null;
      }
  
      const response = await fetch("http://127.0.0.1:8000/cancel", {
        method: "POST"
      });
      
      if (response.ok) {
        console.log("Cancellation confirmed");
        setStatusText('Stopped');
      }
    } catch (error) {
      console.error("Cancellation error:", error);
    }
  };


  async function sendAudioToConversationEndpoint(audioBlob) {
  const requestId = ++currentRequestId.current;
  let isCancelled = false;

  // Reset playback state for new request
  const playbackQueue = [];
  let isPlaying = false;

  // Clear previous audio reference
  if (botAudioRef.current) {
    botAudioRef.current.pause();
    botAudioRef.current = null;
  }

  try {
    const response = await sendAudioToBackend(audioBlob);
    
    // Store the active processor reference
    activeChunkProcessor.current = {
      id: requestId,
      cancel: () => {
        isCancelled = true;
        playbackQueue.length = 0;
      }
    };

    if (!response.body) return;

    const reader = response.body.getReader();
    let accumulatedData = new Uint8Array();

    const playNextChunk = () => {
      if (playbackQueue.length === 0 || isCancelled) {
        isPlaying = false;
        return;
      }

      isPlaying = true;
      const audioBlob = playbackQueue.shift();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      botAudioRef.current = audio;

      audio.play().catch(error => {
        console.error("Error playing audio chunk:", error);
        URL.revokeObjectURL(audioUrl);
        isPlaying = false;
      });

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        isPlaying = false;
        playNextChunk();
      };
    };

    while (!isCancelled && requestId === currentRequestId.current) {
      const { done, value } = await reader.read();
      if (done) break;

      if (isInterruptedRef_beta.current) {
        console.log('Interruption detected during processing');
        await reader.cancel();
        break;
      }

      // Existing chunk processing logic
      if (value && value.byteLength > 0) {
        const combinedData = new Uint8Array(accumulatedData.length + value.length);
        combinedData.set(accumulatedData, 0);
        combinedData.set(value, accumulatedData.length);
        accumulatedData = combinedData;

        let startIndex = 0;
        while (startIndex < accumulatedData.length) {
          const isWavHeader =
            accumulatedData[startIndex] === 82 &&
            accumulatedData[startIndex + 1] === 73 &&
            accumulatedData[startIndex + 2] === 70 &&
            accumulatedData[startIndex + 3] === 70;

          if (isWavHeader) {
            let dataLength = accumulatedData.length - startIndex;
            if (dataLength >= 8) {
              const riffChunkSize = new DataView(accumulatedData.buffer, startIndex + 4, 4).getUint32(0, true) + 8;
              if (dataLength >= riffChunkSize) {
                const wavData = accumulatedData.subarray(startIndex, startIndex + riffChunkSize);
                const chunkBlob = new Blob([wavData], { type: "audio/wav" });
                
                // Only process if still the current request
                if (requestId === currentRequestId.current) {
                  playbackQueue.push(chunkBlob);
                  const botAudioUrl = URL.createObjectURL(chunkBlob);
                  setChatHistory((prev) => [
                    ...prev,
                    { type: "audio", sender: "bot", content: botAudioUrl },
                  ]);
                  if (!isPlaying) playNextChunk();
                }

                startIndex += riffChunkSize;
                continue;
              }
            }
          }
          break;
        }
        accumulatedData = accumulatedData.subarray(startIndex);
      }
    }

    // Final cleanup after processing
    if (requestId === currentRequestId.current) {
      setStatusText('Listening...');
      startRecording();
    }
  } catch (error) {
    if (requestId === currentRequestId.current) {
      console.error("Stream error:", error);
      setChatHistory(prev => [...prev, 
        { type: "text", sender: "bot", content: "Error processing response" }
      ]);
      setStatusText('Listening...');
      startRecording();
    }
  }
}

  const defaultOptions = {
    loop: true,
    autoplay: true,
    animationData: listeningAnimation,
    rendererSettings: {
      preserveAspectRatio: "xMidYMid slice",
    },
  };

  return (
    <div className="voice-chat-container">
      <p className="status-text pulse">{statusText}</p>{" "}
      {/* Status text with pulse */}
      <p className="interrupt-text">{interruptMessage}</p>{" "}
      {/* Interrupt message */}
      <div className="listening-indicator">
        <Lottie options={defaultOptions} height={300} width={300} />
      </div>
      <button className="stop-button" onClick={handleStopButton}>
        <X />
      </button>
    </div>
  );
};

export default VoiceChat;
