import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
import Lottie from 'react-lottie';
import listeningAnimation from "./Animation1.json";
import "./VoiceChat.css";

const VoiceChat = ({ onSelectOption, sendAudioToBackend, playAudioMessage, setChatHistory }) => {
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
    // Stop recording and clear all timeouts
    stopRecordingAndProcess();
    clearTimeout(silenceTimeoutRef.current);
    silenceTimeoutRef.current = null;

    // Stop any ongoing bot audio
    if (botAudioRef.current) {
      botAudioRef.current.pause();
      botAudioRef.current.currentTime = 0;
    }

    // Reset status text
    setStatusText('Stopped');
    setInterruptMessage('');

    onSelectOption('stop');
  };

  const handleDataAvailable = async (event) => {
    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });
      const audioUrl = URL.createObjectURL(audioBlob);

      // Only process if the audio is meaningful
      if (audioBlob.size > 1000) { // Adjust the size threshold as needed
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
          const backendAudioBlob = await response.blob();
          const backendAudioUrl = URL.createObjectURL(backendAudioBlob);

          // Save bot message
          setChatHistory((prev) => [
            ...prev,
            { type: "audio", sender: "bot", content: backendAudioUrl },
          ]);

          const botAudio = new Audio(backendAudioUrl);
          botAudioRef.current = botAudio; // Store the bot's audio reference
          botAudio.play()
            .catch(error => {
              console.error("Audio playback error:", error);
              onSelectOption('voiceHistory');
            });

          // Show interrupt message when bot is responding
          setStatusText('Bot is responding...');
          setInterruptMessage('Start talking to interrupt.');

          // Restart recording after bot response
          botAudio.onended = () => {
            startRecording();
            setStatusText('Listening...');
            setInterruptMessage('');
          };
        } catch (error) {
          console.error("Error sending audio to the backend:", error);
          setChatHistory((prev) => [
            ...prev,
            { type: "text", sender: "bot", content: "Error: Unable to process the audio." },
          ]);
          onSelectOption('voiceHistory');
        }
      }

      // Restart recording immediately after processing
      startRecording();
    }
  };

  const handleStop = () => {
    // Reset logic can go here if needed
  };

  async function sendAudioToConversationEndpoint(audioBlob) {
    const url = "http://127.0.0.1:8000/conversation-audio";
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");

    const response = await fetch(url, { method: "POST", body: formData });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to process audio: ${response.statusText} - ${errorText}`);
    }

    return response;
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
