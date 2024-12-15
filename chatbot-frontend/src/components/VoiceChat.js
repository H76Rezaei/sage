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
  const [selectedGender, setSelectedGender] = useState("male");
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const CHUNK_DURATION = 5000; // 5 seconds for each chunk

  const startRecording = async () => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        const mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            const audioBlob = new Blob([event.data], { type: "audio/webm" });
            sendAudioToConversationEndpoint(audioBlob, selectedGender);
          }
        };

        mediaRecorder.onstop = handleStop;
        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.start(CHUNK_DURATION); // Send chunk every 5 seconds
        setIsRecording(true);
        console.log("Recording...");
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

  const handleStop = () => {
    console.log("Recording stopped.");
  };

  const sendAudioToConversationEndpoint = async (audioBlob, gender) => {
    try {
      const url = "http://127.0.0.1:8000/conversation-audio";
      const formData = new FormData();
      formData.append("audio", audioBlob, "audio.wav");
      formData.append("gender", gender);

      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to process audio: ${errorText}`);
      }

      const backendAudioBlob = await response.blob();
      const backendAudioUrl = URL.createObjectURL(backendAudioBlob);

      setChatHistory((prev) => [
        ...prev,
        { type: "audio", sender: "bot", content: backendAudioUrl },
      ]);

      const audio = new Audio(backendAudioUrl);
      audio
        .play()
        .catch((error) => console.error("Audio playback error:", error));
    } catch (error) {
      console.error("Backend error:", error);
      setChatHistory((prev) => [
        ...prev,
        { type: "text", sender: "bot", content: "Audio processing failed." },
      ]);
    }
  };

  return (
    <div className="voice-chat-container">
      <div className="voice-chat-header">
        <button className="back-button" onClick={() => onSelectOption(null)}>
          <ArrowLeft />
        </button>
        <h1>Voice Chat</h1>
      </div>

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

      <div className="voice-controls">
        <button
          className={`record-button ${isRecording ? "recording" : ""}`}
          onClick={isRecording ? stopRecording : startRecording}
        >
          {isRecording ? (
            <>
              <MicOff />
              <span>Stop Recording</span>
            </>
          ) : (
            <>
              <Mic />
              <span>Start Recording</span>
            </>
          )}
        </button>
      </div>

      <div className="messages-container">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={msg.sender === "user" ? "user-message" : "bot-message"}
          >
            {msg.type === "audio" ? (
              <audio controls src={msg.content} className="audio-player" />
            ) : (
              msg.content
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default VoiceChat;
