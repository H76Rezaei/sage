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

  const navigate = useNavigate();
  const location = useLocation();
  const isVoiceRoute = location.pathname === "/voice";

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
          mediaRecorderRef.current.stream
            .getTracks()
            .forEach((track) => track.stop());
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
              setStatusText("Listening.."); // Display Stopped
              setInterruptMessage("");
              handleInterrupt();
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
              }, 2000);
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
    stopFlagRef.current = true; // Set stop flag to prevent new recordings

    // Stop recording and clean up media recorder
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream
          .getTracks()
          .forEach((track) => track.stop());
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
    setStatusText("Stopped");
    setInterruptMessage("");
  };

  const handleDataAvailable = async (event) => {
    if (stopFlagRef.current || !userSpeakingRef.current) return;

    if (isInterruptedRef.current) {
      isInterruptedRef.current = false;
      startRecording();
      return;
    }

    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });

      if (audioBlob.size > 1000) {
        console.log("User audio recorded:", audioBlob);
        setChatHistory((prev) => [
          ...prev,
          {
            type: "audio",
            sender: "user",
            content: URL.createObjectURL(audioBlob),
          },
        ]);

        try {
          await sendAudioToConversationEndpoint(audioBlob); // Send to backend and play response
          //startRecording(); // Restart recording after bot response
        } catch (error) {
          console.error("Error handling bot audio:", error);
          cleanup();
        }
      }
    }
  };

  const handleInterrupt = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/cancel", {
        method: "POST",
      });
      if (response.ok) {
        console.log("Cancellation confirmed by backend.");

        if (botAudioRef.current) {
          botAudioRef.current.pause();
          botAudioRef.current.currentTime = 0;
          botAudioRef.current = null;
        }
        setStatusText("Stopped"); // Update status to "Stopped" immediately
        isInterruptedRef.current = true;
      } else {
        console.error("Backend failed to confirm cancellation.");
      }
    } catch (error) {
      console.error("Error sending cancellation request:", error);
    }
  };

  async function sendAudioToConversationEndpoint(audioBlob) {
    try {
      const response = await sendAudioToBackend(audioBlob);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Backend error: ${response.status} - ${errorText}`);
        setChatHistory((prev) => [
          ...prev,
          {
            type: "text",
            sender: "bot",
            content: `Error: ${errorText || response.statusText}`,
          },
        ]);
        // Add these lines to restart recording after error
        setStatusText("Listening...");
        startRecording();
        return;
      }

      const reader = response.body.getReader();
      let accumulatedData = new Uint8Array();
      const playbackQueue = [];
      let isPlaying = false;

      const playNextChunk = () => {
        if (playbackQueue.length === 0) {
          isPlaying = false;
          botAudioRef.current = null;
          return;
        }
        isPlaying = true;
        const audioBlob = playbackQueue.shift();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        botAudioRef.current = audio;

        audio.play().catch((error) => {
          console.error("Error playing audio chunk:", error);
          URL.revokeObjectURL(audioUrl);
          playNextChunk();
          botAudioRef.current = null;
        });

        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          playNextChunk();
        };
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("Finished receiving bot audio");
          setStatusText("Listening..."); // Switch back to "Listening"
          startRecording();
          break;
        }

        if (value && value.byteLength > 0) {
          const combinedData = new Uint8Array(
            accumulatedData.length + value.length
          );
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
                const riffChunkSize =
                  new DataView(
                    accumulatedData.buffer,
                    startIndex + 4,
                    4
                  ).getUint32(0, true) + 8;
                if (dataLength >= riffChunkSize) {
                  const wavData = accumulatedData.subarray(
                    startIndex,
                    startIndex + riffChunkSize
                  );
                  const chunkBlob = new Blob([wavData], { type: "audio/wav" });
                  playbackQueue.push(chunkBlob);
                  // Add to chat history *immediately* after pushing to playbackQueue:
                  const botAudioUrl = URL.createObjectURL(chunkBlob); //Create URL right after the blob is created
                  setChatHistory((prev) => [
                    ...prev,
                    { type: "audio", sender: "bot", content: botAudioUrl },
                  ]);
                  if (!isPlaying) playNextChunk();

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

      console.log("All audio chunks processed.");
    } catch (error) {
      console.error("Error streaming audio:", error);
      setChatHistory((prev) => [
        ...prev,
        {
          type: "text",
          sender: "bot",
          content: "Error processing bot response",
        },
      ]);
      setStatusText("Listening...");
      startRecording();
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
