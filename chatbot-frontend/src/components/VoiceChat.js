import React, { useState, useRef } from "react";
import { ArrowLeft, Mic, MicOff } from "lucide-react";
import "./VoiceChat.css";

const VoiceChat = ({
  onSelectOption,
  sendAudioToBackend,
  playAudioMessage,
}) => {
  const [isRecording, setIsRecording] = useState(false); // State to track recording status
  const mediaRecorderRef = useRef(null); // Ref to hold the media recorder instance
  const [chatHistory, setChatHistory] = useState([]); // State to store the chat history (messages or audio)

  // Function to start recording audio when the user clicks the "Start Recording" button
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

        // Define what happens when recording stops
        mediaRecorder.onstop = handleStop;

        // Save the media recorder instance for later use
        mediaRecorderRef.current = mediaRecorder;

        // Start recording
        mediaRecorder.start();

        // Update state to reflect that the recording has started
        setIsRecording(true);
      } catch (err) {
        console.error("Error accessing audio devices:", err);
      }
    }
  };

  // Function to stop recording when the user clicks the "Stop Recording" button
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  // Function to handle data when recording stops (audio chunk is available)
  const handleDataAvailable = (event) => {
    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });
      const audioUrl = URL.createObjectURL(audioBlob);

      setChatHistory((prev) => [
        ...prev,
        { type: "audio", sender: "user", content: audioUrl },
      ]);

      // Send the raw audio blob to the conversation-audio endpoint
      sendAudioToConversationEndpoint(audioBlob)
        .then(async (response) => {
          // Create a URL for the audio blob returned from the backend
          const audioBlob = await response.blob();
          const audioUrl = URL.createObjectURL(audioBlob);

          // Update chat history with the bot's audio response
          setChatHistory((prev) => [
            ...prev,
            { type: "audio", sender: "bot", content: audioUrl },
          ]);

          // Play the bot's response as audio
          // comment this part of the code to stop the audio from automatically playing
          const audio = new Audio(audioUrl);
          //comment this line too
          audio.play().catch(error => console.error("Audio playback error:", error));
          //end of comment
        })
        .catch((error) => {
          console.error("Error sending audio to the backend:", error);
          setChatHistory((prev) => [
            ...prev,
            {
              type: "text",
              sender: "bot",
              content: "Error: Unable to process the audio.",
            },
          ]);
        });
    }
  };

  // Function to handle the stop of the recording (no specific logic here yet)
  const handleStop = () => {
    // Reset logic can go here if needed
  };

  // Utility function to convert Blob to WAV format (if necessary)
  const convertBlobToWav = (audioBlob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const arrayBuffer = reader.result;
        const wavBlob = new Blob([arrayBuffer], { type: "audio/wav" });
        resolve(wavBlob); // Return the converted WAV blob
      };
      reader.onerror = (err) => reject(err);
      reader.readAsArrayBuffer(audioBlob); // Read the audio as an array buffer
    });
  };

  // Function to send audio to the conversation-audio endpoint
  async function sendAudioToConversationEndpoint(audioBlob) {
    const url = "http://127.0.0.1:8000/conversation-audio";
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");

    const response = await fetch(url, { method: "POST", body: formData });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to process audio: ${response.statusText} - ${errorText}`);
    }

    return response; // Return the response directly to handle as a blob
  }

  return (
    <div className="voice-chat-container">
      {/* Header Section */}
      <div className="voice-chat-header">
        <button className="back-button" onClick={() => onSelectOption(null)}>
          <ArrowLeft />
        </button>
        <h1>Voice Chat</h1>
      </div>

      {/* Chat History Section */}
      <div className="messages-container">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={`message ${
              msg.sender === "user" ? "user-message" : "bot-message"
            }`}
          >
            {msg.type === "audio" ? (
              <audio controls src={msg.content} className="audio-player" />
            ) : (
              msg.content
            )}
          </div>
        ))}

        {/* Display an animation when recording */}
        {isRecording && (
          <div className="listening-indicator">
            <div className="listening-text">Listening...</div>
            <div className="wave-container">
              <div className="wave"></div>
              <div className="wave"></div>
              <div className="wave"></div>
              <div className="wave"></div>
              <div className="wave"></div>
            </div>
          </div>
        )}
      </div>

      {/* Recording Controls */}
      <div className="voice-controls">
        <button
          className={`record-button ${isRecording ? "recording" : ""}`}
          onClick={isRecording ? stopRecording : startRecording}
        >
          {isRecording ? (
            <>
              <MicOff className="mic-icon" />
              <span>Stop Recording</span>
            </>
          ) : (
            <>
              <Mic className="mic-icon" />
              <span>Start Recording</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default VoiceChat;
