import React, { useState, useRef } from "react";
import { ArrowLeft, Mic, MicOff } from "lucide-react";
import "./VoiceChat.css";

const VoiceChat = ({
  onSelectOption,
  sendAudioToBackend,
  playAudioMessage,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const [chatHistory, setChatHistory] = useState([]);

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
      const chunk = event.data;
      chunksRef.current.push(chunk);
      await sendChunkToAPI(chunk);
    }
  };

  const handleStop = () => {
    const audioBlob = new Blob(chunksRef.current, { type: "audio/wav" });
    const audioUrl = URL.createObjectURL(audioBlob);

    setChatHistory((prev) => [
      ...prev,
      { type: "audio", sender: "user", content: audioUrl },
    ]);

    sendAudioToBackend(audioBlob)
      .then(async (response) => {
        if (response && response.data) {
          const botAudioUrl = response.data.audioUrl;
          setChatHistory((prev) => [
            ...prev,
            { type: "audio", sender: "bot", content: botAudioUrl },
          ]);

          await playAudioMessage(botAudioUrl);
        }
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

    chunksRef.current = [];
  };

  const sendChunkToAPI = async (chunk) => {
    const formData = new FormData();
    formData.append("audio", chunk, `chunk-${Date.now()}.webm`);

    try {
      const response = await fetch("/api/upload-audio-chunk", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to upload audio chunk");
      }
    } catch (error) {
      console.error("Error uploading audio chunk:", error);
    }
  };

  return (
    <div className="voice-chat-container">
      {/* Header */}
      <div className="voice-chat-header">
        <button className="back-button" onClick={() => onSelectOption(null)}>
          <ArrowLeft />
        </button>
        <h1>Voice Chat</h1>
      </div>

      {/* Chat Messages */}
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

        {/* Animation when recording */}
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
