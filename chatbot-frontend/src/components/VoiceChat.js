import React, { useState, useRef } from "react";
import { ArrowLeft, Mic, MicOff } from "lucide-react";
import "./VoiceChat.css";

const VoiceChat = ({
  onSelectOption,
  sendAudioToBackend,
  playAudioMessage,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedGender, setSelectedGender] = useState("male"); // State to track selected voice gender
  const mediaRecorderRef = useRef(null);

  const startRecording = async () => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        const mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = handleDataAvailable;
        mediaRecorder.onstop = handleStop;

        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Error accessing audio devices:", err);
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const handleDataAvailable = async (event) => {
    if (event.data.size > 0) {
      const audioBlob = new Blob([event.data], { type: "audio/webm" });
      const audioUrl = URL.createObjectURL(audioBlob);

      setChatHistory((prev) => [
        ...prev,
        { type: "audio", sender: "user", content: audioUrl },
      ]);

      try {
        const response = await sendAudioToConversationEndpoint(
          audioBlob,
          selectedGender
        );

        const backendAudioBlob = await response.blob();
        const backendAudioUrl = URL.createObjectURL(backendAudioBlob);

        setChatHistory((prev) => [
          ...prev,
          { type: "audio", sender: "bot", content: backendAudioUrl },
        ]);

        // Automatically play audio response
        const audio = new Audio(backendAudioUrl);
        audio
          .play()
          .catch((error) => console.error("Audio playback error:", error));
      } catch (error) {
        console.error("Error sending audio to the backend:", error);
        setChatHistory((prev) => [
          ...prev,
          {
            type: "text",
            sender: "bot",
            content: "Error: Unable to process the audio.",
          },
        ]);
      }
    }
  };

  const handleStop = () => {};

  const sendAudioToConversationEndpoint = async (audioBlob, gender) => {
    const url = "http://127.0.0.1:8000/conversation-audio";
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");
    formData.append("gender", gender); // Pass the gender parameter to the backend

    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to process audio: ${response.statusText} - ${errorText}`
      );
    }

    return response;
  };

  return (
    <div className="voice-chat-container">
      {/* Header Section */}
      <div className="voice-chat-header">
        <button className="back-button" onClick={() => onSelectOption(null)}>
          <ArrowLeft />
        </button>
        <h1>Voice Chat</h1>
      </div>

      {/* Voice Gender Selection Dropdown */}
      <div className="voice-gender-selector">
        <label htmlFor="voice-gender">Select Voice Gender:</label>
        <select
          id="voice-gender"
          value={selectedGender}
          onChange={(e) => setSelectedGender(e.target.value)}
        >
          <option value="male">Male</option>
          <option value="female">Female</option>
        </select>
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
