import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from "react-lottie";
import listeningAnimation from "./Animation.json";
import "./Voice.css";
import { sendAudioToBackend } from "../services/speechApi";
import { useNavigate, useLocation } from "react-router-dom";

const VoiceChat = ({ onSelectOption, sendAudioToBackend, setChatHistory }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [interruptMessage, setInterruptMessage] = useState("");

  const currentRequestId = useRef(0);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const botAudioRef = useRef(null);
  const silenceTimeoutRef = useRef(null);

  const userSpeakingRef = useRef(false);
  const silenceDetectionStartedRef = useRef(false);
  const isRecordingRef = useRef(false);
  const isProcessingRef = useRef(false);

  const navigate = useNavigate();
  const location = useLocation();
  const isVoiceRoute = location.pathname === "/voice";

  
  const resumeRecording = () => {
    if (isVoiceRoute) {
      console.log("Resuming recording.");
      cleanup();
      setStatusText("Listening...");
      startRecording();
    }
  };

  useEffect(() => {
    if (isVoiceRoute && !isRecording) {
      startRecording();
    } else if (!isVoiceRoute && isRecording) {
      cleanup();
    }
    
  }, [isVoiceRoute]);

 
  useEffect(() => {
    if (location.pathname !== "/voice") {
      console.log("Route changed away from /voice, cleaning up voice chat.");
      cleanup();
    }
    
  }, [location.pathname]);

  
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

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

  const startRecording = async () => {
    if (!isVoiceRoute || isRecording) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream
          .getTracks()
          .forEach((track) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = handleDataAvailable;
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.start();
      setStatusText("Listening...");
      console.log("Recording started.");
      setIsRecording(true);
      isRecordingRef.current = true;
      isProcessingRef.current = false;

      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      audioContextRef.current = audioContext;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const volumeThreshold = 40;

      const detectSilence = () => {
        if (!isRecordingRef.current) return;
        analyser.getByteFrequencyData(dataArray);
        const avgVolume =
          dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

        if (avgVolume > volumeThreshold) {
          userSpeakingRef.current = true;
          silenceDetectionStartedRef.current = true;

          if (botAudioRef.current && !botAudioRef.current.paused) {
            console.log("User speaking, interrupting bot audio.");
            botAudioRef.current.pause();
            botAudioRef.current.currentTime = 0;
            setStatusText("Stopped.");
            handleInterrupt();
          }

          if (silenceTimeoutRef.current) {
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }
        } else if (silenceDetectionStartedRef.current) {
          if (!silenceTimeoutRef.current && !isProcessingRef.current) {
            silenceTimeoutRef.current = setTimeout(() => {
              console.log("Silence detected, stopping recording...");
              stopRecordingAndProcess();
              silenceDetectionStartedRef.current = false;
            }, 1000);
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

  const stopRecordingAndProcess = () => {
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setStatusText("Processing...");
  };

  const handleStopButton = () => {
    cleanup();
    navigate("/voice-history");
  };

  const cleanup = () => {
    currentRequestId.current++;
    console.log("Cleanup invoked; cancellation token increased.");

    isRecordingRef.current = false;

    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream
          .getTracks()
          .forEach((track) => track.stop());
      }
      mediaRecorderRef.current = null;
    }

    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    userSpeakingRef.current = false;
    silenceDetectionStartedRef.current = false;
    setIsRecording(false);
    setStatusText("Stopped");
    setInterruptMessage("");
  };

  const handleDataAvailable = async (event) => {
    if (!userSpeakingRef.current) return;
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
          await sendAudioToConversationEndpoint(audioBlob);
        } catch (error) {
          console.error("Error handling bot audio:", error);
          cleanup();
          resumeRecording();
        }
      }
    }
  };

  const handleInterrupt = async () => {
    console.log("Interrupt requested.");
    currentRequestId.current++;
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
      botAudioRef.current = null;
    }
    setStatusText("Stopped");
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
    cleanup();
    resumeRecording();
  };

  async function sendAudioToConversationEndpoint(audioBlob) {
    const requestId = ++currentRequestId.current;
    console.log("New audio request started with token:", requestId);
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current = null;
    }
    const playbackQueue = [];
    let isPlaying = false;
    let streamEnded = false;

    const playNextChunk = () => {
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
        if (requestId !== currentRequestId.current) {
          console.log("Audio processing cancelled.");
          await reader.cancel();
          break;
        }
        const { done, value } = await reader.read();
        if (done) break;
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
      streamEnded = true;
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
