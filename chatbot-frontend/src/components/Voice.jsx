import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from "react-lottie";
import listeningAnimation from "./Animation.json";
import "./Voice.css";
import { sendAudioToBackend } from "../services/speechApi";
import { useNavigate, useLocation } from "react-router-dom";

const VoiceChat = ({ onSelectOption, sendAudioToBackend, setChatHistory }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState(""); // For text status
  const [interruptMessage, setInterruptMessage] = useState(""); // For interrupt message

  // Consolidated cancellation token. Incrementing cancels any in-flight requests.
  const currentRequestId = useRef(0);

  // Refs for media and audio processing.
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const botAudioRef = useRef(null);
  const silenceTimeoutRef = useRef(null);

  // Refs for controlling silence detection and recording loops.
  const userSpeakingRef = useRef(false);
  const silenceDetectionStartedRef = useRef(false);
  const isRecordingRef = useRef(false); // Tracks whether we should keep running detectSilence
  const isProcessingRef = useRef(false); // Guard to avoid multiple stop calls

  const navigate = useNavigate();
  const location = useLocation();
  const isVoiceRoute = location.pathname === "/voice";

  // Helper to resume recording by cleaning up any existing session first.
  const resumeRecording = () => {
    if (isVoiceRoute) {
      console.log("Resuming recording.");
      cleanup(); // Make sure the previous session is completely cleaned up.
      setStatusText("Listening...");
      startRecording();
    }
  };

  // Start or stop recording based on the route.
  useEffect(() => {
    if (isVoiceRoute && !isRecording) {
      startRecording();
    } else if (!isVoiceRoute && isRecording) {
      cleanup();
    }
    return () => {
      if (isRecording) {
        cleanup();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVoiceRoute]);

  // Clear voice history on unload.
  const clearVoiceHistory = () => {
    localStorage.removeItem("voiceChatHistory");
    if (setChatHistory) {
      setChatHistory([]);
    }
  };

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

  // Start recording audio.
  const startRecording = async () => {
    // Note: We now expect isRecording to be false because resumeRecording calls cleanup first.
    if (!isVoiceRoute || isRecording) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Clean up previous media if any.
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = handleDataAvailable;
      mediaRecorderRef.current = mediaRecorder;

      // Start recording.
      mediaRecorder.start();
      setStatusText("Listening...");
      console.log("Recording started.");
      setIsRecording(true);
      isRecordingRef.current = true;
      isProcessingRef.current = false; // Reset processing flag on new recording

      // Set up an audio context and analyser for silence detection.
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      audioContextRef.current = audioContext;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const volumeThreshold = 70; // Adjust threshold as needed

      // Recursive function for silence detection.
      const detectSilence = () => {
        // If recording has been cancelled, stop further processing.
        if (!isRecordingRef.current) return;

        analyser.getByteFrequencyData(dataArray);
        const avgVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

        if (avgVolume > volumeThreshold) {
          // User is speaking.
          userSpeakingRef.current = true;
          silenceDetectionStartedRef.current = true;

          // If bot audio is playing, interrupt it.
          if (botAudioRef.current && !botAudioRef.current.paused) {
            console.log("User speaking, interrupting bot audio.");
            botAudioRef.current.pause();
            botAudioRef.current.currentTime = 0;
            setStatusText("Stopped.");
            handleInterrupt(); // Cancel any ongoing processing.
          }

          // Clear any scheduled silence timeout.
          if (silenceTimeoutRef.current) {
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }
        } else if (silenceDetectionStartedRef.current) {
          // When silence is detected, schedule stopping the recording.
          if (!silenceTimeoutRef.current && !isProcessingRef.current) {
            silenceTimeoutRef.current = setTimeout(() => {
              console.log("Silence detected, stopping recording...");
              stopRecordingAndProcess();
              silenceDetectionStartedRef.current = false;
            }, 2000);
          }
        }
        requestAnimationFrame(detectSilence);
      };

      detectSilence();
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

  // Stop recording and begin processing.
  const stopRecordingAndProcess = () => {
    // Guard against multiple calls.
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setStatusText("Processing...");
  };

  // Handler for the stop button.
  const handleStopButton = () => {
    cleanup();
    navigate("/voice-history");
  };

  // Cleanup all resources and cancel ongoing requests.
  const cleanup = () => {
    // Increase the cancellation token.
    currentRequestId.current++;
    console.log("Cleanup invoked; cancellation token increased.");

    // Stop the recording loop.
    isRecordingRef.current = false;

    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
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

  // Called when a data chunk is available.
  const handleDataAvailable = async (event) => {
    // If no user speech has been detected, ignore this data.
    if (!userSpeakingRef.current) return;

    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });

      // Only process if the blob is sufficiently large.
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
          resumeRecording();
        }
      }
    }
  };

  // Interrupt processing by bumping the cancellation token.
  const handleInterrupt = async () => {
    console.log("Interrupt requested.");
    // Bump the cancellation token.
    currentRequestId.current++;
  
    // Stop any playing bot audio.
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }
  
    setStatusText("Stopped");
  
    // Optionally notify the server of the cancellation.
    try {
      const response = await fetch("http://127.0.0.1:8000/cancel", { method: "POST" });
      if (response.ok) {
        console.log("Cancellation confirmed on the server.");
      }
    } catch (error) {
      console.error("Cancellation error:", error);
    }
  
    // Clear any lingering resources.
    cleanup();
  
    // Immediately resume recording after an interruption.
    resumeRecording();
  };
  

  // Send audio to the backend and process the streamed response.
  // Send audio to the backend and process the streamed response.
async function sendAudioToConversationEndpoint(audioBlob) {
  const requestId = ++currentRequestId.current;
  console.log("New audio request started with token:", requestId);

  // Reset any bot audio playback.
  if (botAudioRef.current) {
    botAudioRef.current.pause();
    botAudioRef.current = null;
  }

  // Queue for sequential playback.
  const playbackQueue = [];
  let isPlaying = false;
  let streamEnded = false; // Flag to indicate if the stream reading is done.

  const playNextChunk = () => {
    // If no more chunks and stream has ended, resume recording.
    if (playbackQueue.length === 0) {
      isPlaying = false;
      if (streamEnded && requestId === currentRequestId.current) {
        console.log("All chunks played; resuming recording.");
        resumeRecording();
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
      // Even if there's an error, we try to play the next chunk.
      playNextChunk();
    });

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      isPlaying = false;
      playNextChunk();
    };
  };

  try {
    const response = await sendAudioToBackend(audioBlob);
    if (!response.body) return;

    const reader = response.body.getReader();
    let accumulatedData = new Uint8Array();

    while (true) {
      // Exit early if cancelled.
      if (requestId !== currentRequestId.current) {
        console.log("Audio processing cancelled.");
        await reader.cancel();
        break;
      }
      const { done, value } = await reader.read();
      if (done) break;

      if (value && value.byteLength > 0) {
        // Accumulate new data.
        const combinedData = new Uint8Array(accumulatedData.length + value.length);
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
                new DataView(accumulatedData.buffer, startIndex + 4, 4).getUint32(0, true) + 8;
              if (dataLength >= riffChunkSize) {
                const wavData = accumulatedData.subarray(startIndex, startIndex + riffChunkSize);
                const chunkBlob = new Blob([wavData], { type: "audio/wav" });

                // Process only if still current.
                if (requestId === currentRequestId.current) {
                  playbackQueue.push(chunkBlob);
                  const botAudioUrl = URL.createObjectURL(chunkBlob);
                  setChatHistory((prev) => [
                    ...prev,
                    { type: "audio", sender: "bot", content: botAudioUrl },
                  ]);
                  // Start playback if not already playing.
                  if (!isPlaying) {
                    playNextChunk();
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
    if (!isPlaying && playbackQueue.length === 0 && requestId === currentRequestId.current) {
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
