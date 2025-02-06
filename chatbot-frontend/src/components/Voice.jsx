import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from "react-lottie";
import listeningAnimation from "./Animation.json";
import "./Voice.css";
import { sendAudioToBackend } from "../services/speechApi";
import { useNavigate, useLocation } from "react-router-dom";

// Main VoiceChat component for handling voice-based interactions.
const VoiceChat = ({ onSelectOption, sendAudioToBackend, setChatHistory }) => {
  // State to track if recording is active.
  const [isRecording, setIsRecording] = useState(false);
  // State to display status text (e.g., "Listening...", "Processing...").
  const [statusText, setStatusText] = useState("");
  // State to display interrupt messages (e.g., when bot audio is interrupted).
  const [interruptMessage, setInterruptMessage] = useState("");

  // Ref to track the current request ID for cancellation purposes.
  const currentRequestId = useRef(0);

  // Refs for managing media and audio processing.
  const mediaRecorderRef = useRef(null); // MediaRecorder instance.
  const audioContextRef = useRef(null); // AudioContext for silence detection.
  const botAudioRef = useRef(null); // Reference to the bot's audio element.
  const silenceTimeoutRef = useRef(null); // Timeout for silence detection.

  // Refs for controlling silence detection and recording loops.
  const userSpeakingRef = useRef(false); // Tracks if the user is speaking.
  const silenceDetectionStartedRef = useRef(false); // Tracks if silence detection is active.
  const isRecordingRef = useRef(false); // Tracks if recording is ongoing.
  const isProcessingRef = useRef(false); // Guards against multiple stop calls.

  // React Router hooks for navigation and location.
  const navigate = useNavigate();
  const location = useLocation();
  const isVoiceRoute = location.pathname === "/voice"; // Checks if the current route is "/voice".

  // Helper function to resume recording after cleanup.
  const resumeRecording = () => {
    if (isVoiceRoute) {
      console.log("Resuming recording.");
      cleanup(); // Clean up any existing session.
      setStatusText("Listening...");
      startRecording(); // Start a new recording session.
    }
  };

  // Effect to start or stop recording based on the route.
  useEffect(() => {
    if (isVoiceRoute && !isRecording) {
      startRecording(); // Start recording if on the voice route.
    } else if (!isVoiceRoute && isRecording) {
      cleanup(); // Clean up if leaving the voice route.
    }
    return () => {
      if (isRecording) {
        cleanup(); // Clean up on component unmount.
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVoiceRoute]);

  // Function to clear voice chat history from localStorage.
  const clearVoiceHistory = () => {
    localStorage.removeItem("voiceChatHistory");
    if (setChatHistory) {
      setChatHistory([]); // Reset chat history in state.
    }
  };

  // Effect to clear voice history on page unload.
  useEffect(() => {
    const handleBeforeUnload = () => {
      clearVoiceHistory();
    };
    clearVoiceHistory();
    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("unload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("unload", handleBeforeUnload);
    };
  }, []);

  // Function to start recording audio.
  const startRecording = async () => {
    // Exit if not on the voice route or already recording.
    if (!isVoiceRoute || isRecording) return;

    try {
      // Request access to the user's microphone.
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Clean up previous media resources if any.
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream
          .getTracks()
          .forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }

      // Create a new MediaRecorder instance.
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = handleDataAvailable; // Set handler for data availability.
      mediaRecorderRef.current = mediaRecorder;

      // Start recording.
      mediaRecorder.start();
      setStatusText("Listening...");
      console.log("Recording started.");
      setIsRecording(true);
      isRecordingRef.current = true;
      isProcessingRef.current = false; // Reset processing flag.

      // Set up audio context and analyser for silence detection.
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      audioContextRef.current = audioContext;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const volumeThreshold = 20; // Threshold for detecting speech.

      // Recursive function to detect silence.
      const detectSilence = () => {
        if (!isRecordingRef.current) return; // Exit if recording is stopped.

        analyser.getByteFrequencyData(dataArray);
        const avgVolume =
          dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

        if (avgVolume > volumeThreshold) {
          // User is speaking.
          userSpeakingRef.current = true;
          silenceDetectionStartedRef.current = true;

          // Interrupt bot audio if playing.
          if (botAudioRef.current && !botAudioRef.current.paused) {
            console.log("User speaking, interrupting bot audio.");
            botAudioRef.current.pause();
            botAudioRef.current.currentTime = 0;
            setStatusText("Stopped.");
            handleInterrupt(); // Cancel ongoing processing.
          }

          // Clear any scheduled silence timeout.
          if (silenceTimeoutRef.current) {
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }
        } else if (silenceDetectionStartedRef.current) {
          // Schedule stopping the recording after silence.
          if (!silenceTimeoutRef.current && !isProcessingRef.current) {
            silenceTimeoutRef.current = setTimeout(() => {
              console.log("Silence detected, stopping recording...");
              stopRecordingAndProcess();
              silenceDetectionStartedRef.current = false;
            }, 1000);
          }
        }
        requestAnimationFrame(detectSilence); // Continue detecting silence.
      };

      detectSilence(); // Start silence detection.
    } catch (err) {
      console.error("Error accessing audio devices:", err);
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
  };

  // Function to stop recording and begin processing.
  const stopRecordingAndProcess = () => {
    if (isProcessingRef.current) return; // Guard against multiple calls.
    isProcessingRef.current = true;
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop(); // Stop the MediaRecorder.
    }
    setStatusText("Processing...");
  };

  // Handler for the stop button.
  const handleStopButton = () => {
    cleanup(); // Clean up resources.
    navigate("/voice-history"); // Navigate to the voice history page.
  };

  // Function to clean up all resources and cancel ongoing requests.
  const cleanup = () => {
    currentRequestId.current++; // Increment cancellation token.
    console.log("Cleanup invoked; cancellation token increased.");

    isRecordingRef.current = false; // Stop the recording loop.

    // Stop and release MediaRecorder resources.
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream
          .getTracks()
          .forEach((track) => track.stop());
      }
      mediaRecorderRef.current = null;
    }

    // Pause and release bot audio.
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }

    // Close the audio context.
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Clear any silence timeout.
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    // Reset flags.
    userSpeakingRef.current = false;
    silenceDetectionStartedRef.current = false;
    setIsRecording(false);
    setStatusText("Stopped");
    setInterruptMessage("");
  };

  // Handler for when audio data is available.
  const handleDataAvailable = async (event) => {
    if (!userSpeakingRef.current) return; // Ignore if no user speech detected.

    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });

      // Only process if the blob is sufficiently large.
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
          await sendAudioToConversationEndpoint(audioBlob); // Send audio to backend.
        } catch (error) {
          console.error("Error handling bot audio:", error);
          cleanup();
          resumeRecording();
        }
      }
    }
  };

  // Function to interrupt processing by bumping the cancellation token.
  const handleInterrupt = async () => {
    console.log("Interrupt requested.");
    currentRequestId.current++; // Bump the cancellation token.

    // Stop any playing bot audio.
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }

    setStatusText("Stopped");

    // Notify the server of the cancellation.
    try {
      const response = await fetch("http://127.0.0.1:8000/cancel", {
        method: "POST",
      });
      if (response.ok) {
        console.log("Cancellation confirmed on the server.");
      }
    } catch (error) {
      console.error("Cancellation error:", error);
    }

    cleanup(); // Clean up resources.
    resumeRecording(); // Resume recording after interruption.
  };

  // Function to send audio to the backend and process the streamed response.
  async function sendAudioToConversationEndpoint(audioBlob) {
    const requestId = ++currentRequestId.current;
    console.log("New audio request started with token:", requestId);

    // Reset any bot audio playback.
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current = null;
    }

    // Queue for sequential playback of audio chunks.
    const playbackQueue = [];
    let isPlaying = false;
    let streamEnded = false; // Flag to indicate if the stream reading is done.

    // Function to play the next audio chunk in the queue.
    const playNextChunk = () => {
      if (playbackQueue.length === 0) {
        isPlaying = false;
        if (streamEnded && requestId === currentRequestId.current) {
          console.log("All chunks played; resuming recording.");
          resumeRecording(); // Resume recording after all chunks are played.
        }
        return;
      }
      isPlaying = true;
      const chunkBlob = playbackQueue.shift();
      const audioUrl = URL.createObjectURL(chunkBlob);
      const audio = new Audio(audioUrl);
      botAudioRef.current = audio;

      audio.play().catch((error) => {
        console.error("Error playing audio chunk:", error);
        URL.revokeObjectURL(audioUrl);
        isPlaying = false;
        playNextChunk(); // Try playing the next chunk even if there's an error.
      });

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        isPlaying = false;
        playNextChunk(); // Play the next chunk after the current one ends.
      };
    };

    try {
      const response = await sendAudioToBackend(audioBlob); // Send audio to the backend.
      if (!response.body) return;

      const reader = response.body.getReader();
      let accumulatedData = new Uint8Array();

      // Process the streamed response.
      while (true) {
        if (requestId !== currentRequestId.current) {
          console.log("Audio processing cancelled.");
          await reader.cancel();
          break;
        }
        const { done, value } = await reader.read();
        if (done) break;

        if (value && value.byteLength > 0) {
          // Accumulate new data.
          const combinedData = new Uint8Array(
            accumulatedData.length + value.length
          );
          combinedData.set(accumulatedData, 0);
          combinedData.set(value, accumulatedData.length);
          accumulatedData = combinedData;

          // Look for a WAV header (RIFF).
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

                  // Process only if still current.
                  if (requestId === currentRequestId.current) {
                    playbackQueue.push(chunkBlob);
                    const botAudioUrl = URL.createObjectURL(chunkBlob);
                    setChatHistory((prev) => [
                      ...prev,
                      { type: "audio", sender: "bot", content: botAudioUrl },
                    ]);
                    if (!isPlaying) {
                      playNextChunk(); // Start playback if not already playing.
                    }
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

      // Mark that the stream has ended.
      streamEnded = true;
      // If nothing is playing and the queue is empty, resume recording immediately.
      if (
        !isPlaying &&
        playbackQueue.length === 0 &&
        requestId === currentRequestId.current
      ) {
        console.log("Stream ended and no pending chunks; resuming recording.");
        resumeRecording();
      }
    } catch (error) {
      console.error("Stream error:", error);
      setChatHistory((prev) => [
        ...prev,
        { type: "text", sender: "bot", content: "Error processing response" },
      ]);
      resumeRecording();
    }
  }

  // Lottie animation options.
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
      <p className="status-text pulse">{statusText}</p>
      <p className="interrupt-text">{interruptMessage}</p>
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
