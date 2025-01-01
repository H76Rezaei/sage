import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from "react-lottie";
import listeningAnimation from "./Animation.json";
import "./Voice.css";
import { sendAudioToBackend } from "../services/speechApi";

const Voice = ({
  onSelectOption,
  sendAudioToBackend,
  playAudioMessage,
  setChatHistory,
}) => {
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
        const volumeThreshold = 15; // Adjust this threshold as needed

        const detectSilence = () => {
          analyser.getByteFrequencyData(dataArray);
          const avgVolume =
            dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

          // Detect meaningful speech and start silence detection
          if (avgVolume > volumeThreshold) {
            userSpeakingRef.current = true; // User started speaking
            silenceDetectionStartedRef.current = true; // Start silence detection

            // If bot is responding, interrupt it
            if (botAudioRef.current) {
              botAudioRef.current.pause();
              botAudioRef.current.currentTime = 0;
              setStatusText("Listening...");
              setInterruptMessage("");
            }

            // Clear the silence timeout if the user is speaking
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }

          // Detect silence only if user has started speaking
          if (
            silenceDetectionStartedRef.current &&
            avgVolume <= volumeThreshold
          ) {
            if (!stopFlagRef.current && silenceTimeoutRef.current === null) {
              silenceTimeoutRef.current = setTimeout(() => {
                if (silenceDetectionStartedRef.current) {
                  console.log("Silence detected, stopping recording...");
                  stopRecordingAndProcess(); // Stop recording and process
                  silenceDetectionStartedRef.current = false; // Reset silence detection flag
                }
              }, 2000); // Stop after 2 seconds of silence
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
    onSelectOption("stop");
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
    // Don't process data if stop flag is set
    if (stopFlagRef.current) return;

    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });
      const audioUrl = URL.createObjectURL(audioBlob);

      // Only process if the audio is meaningful and stop flag is not set
      if (audioBlob.size > 1000 && !stopFlagRef.current) {
        // Save user message
        setChatHistory((prev) => [
          ...prev,
          { type: "audio", sender: "user", content: audioUrl },
        ]);

        // Stop bot's response if new message is detected
        if (botAudioRef.current) {
          botAudioRef.current.pause();
          botAudioRef.current.currentTime = 0;
        }

        try {
          const response = await sendAudioToConversationEndpoint(audioBlob);

          // Check stop flag again after getting response
          if (stopFlagRef.current) {
            // If stopped during processing, don't play or save response
            return;
          }

          const backendAudioBlob = await response.blob();
          const backendAudioUrl = URL.createObjectURL(backendAudioBlob);

          // Save bot message
          setChatHistory((prev) => [
            ...prev,
            { type: "audio", sender: "bot", content: backendAudioUrl },
          ]);

          // Only play if not stopped
          if (!stopFlagRef.current) {
            const botAudio = new Audio(backendAudioUrl);
            botAudioRef.current = botAudio; // Store the bot's audio reference

            botAudio.play().catch((error) => {
              console.error("Audio playback error:", error);

              // Add a text fallback message
              setChatHistory((prev) => [
                ...prev,
                {
                  type: "text",
                  sender: "bot",
                  content:
                    "Sorry, I had trouble responding. Could you please try again?",
                },
              ]);

              // Restart recording
              startRecording();
            });

            // Show interrupt message when bot is responding
            setStatusText("Bot is responding...");
            setInterruptMessage("Start talking to interrupt.");

            // Restart recording after bot response
            botAudio.onended = () => {
              if (!stopFlagRef.current) {
                // Only restart if not stopped
                startRecording();
                setStatusText("Listening...");
                setInterruptMessage("");
              }
            };
          }
        } catch (error) {
          console.error("Error sending audio to the backend:", error);

          // Add a text fallback message
          setChatHistory((prev) => [
            ...prev,
            {
              type: "text",
              sender: "bot",
              content:
                "Sorry, I had trouble understanding your message. Could you please try speaking again?",
            },
          ]);

          // Restart recording
          startRecording();
        }
      }

      // Only restart recording if not stopped
      if (!stopFlagRef.current) {
        startRecording();
      }
    }
  };

  const handleStop = () => {
    // Reset logic can go here if needed
  };

  async function sendAudioToConversationEndpoint(audioBlob) {
    try {
      const response = await sendAudioToBackend(audioBlob);
      console.log("Processed response:", response);
      return response;
    } catch (error) {
      console.error("Error sending audio to the backend:", error);
      throw error;
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
      <p className="interrupt-text">{interruptMessage}</p>{" "}
      <div className="listening-indicator">
        <Lottie options={defaultOptions} height={300} width={300} />
      </div>
      <button className="stop-button" onClick={handleStopButton}>
        <X />
      </button>
    </div>
  );
};

export default Voice;
