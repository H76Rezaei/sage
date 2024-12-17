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

          // Detect meaningful speech and start silence detection
          if (avgVolume > volumeThreshold) {
            userSpeakingRef.current = true; // User started speaking
            silenceDetectionStartedRef.current = true; // Start silence detection

            // If bot is responding, interrupt it
            if (botAudioRef.current) {
              botAudioRef.current.pause();
              botAudioRef.current.currentTime = 0;
              setStatusText('Listening...');
              setInterruptMessage('');
            }

            // Clear the silence timeout if the user is speaking
            clearTimeout(silenceTimeoutRef.current);
            silenceTimeoutRef.current = null;
          }

          // Detect silence only if user has started speaking
          if (silenceDetectionStartedRef.current && avgVolume <= volumeThreshold) {
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
      await sendAudioToBackend(audioBlob); // Pass the blob to the backend for processing
      console.log("Audio chunks enqueued for playback.");
    } catch (error) {
      console.error("Error processing audio in conversation endpoint:", error);
      throw error;
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
