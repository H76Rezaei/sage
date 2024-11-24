import React, { useState, useEffect } from 'react';
import { ArrowLeft, Mic, MicOff } from 'lucide-react';
import './VoiceChat.css';

const VoiceChat = ({ onSelectOption, sendAudioToBackend, playAudioMessage }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);

  useEffect(() => {
    setupMediaRecorder();
  }, []);

  const setupMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          setAudioChunks((chunks) => [...chunks, event.data]);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);

        setChatHistory((prev) => [
          ...prev,
          { type: 'audio', sender: 'user', content: audioUrl }
        ]);

        try {
          // Send the audio to the backend
          const response = await sendAudioToBackend(audioBlob);

          // Display the bot's audio message in the chat
          if (response && response.data) {
            const botAudioUrl = response.data.audioUrl; // Replace with your API response field
            setChatHistory((prev) => [
              ...prev,
              { type: 'audio', sender: 'bot', content: botAudioUrl }
            ]);

            // Optionally play the bot's response
            await playAudioMessage(botAudioUrl);
          }
        } catch (error) {
          console.error('Error sending audio to the backend:', error);
          setChatHistory((prev) => [
            ...prev,
            { type: 'text', sender: 'bot', content: 'Error: Unable to process the audio.' }
          ]);
        }

        setAudioChunks([]);
      };

      setMediaRecorder(recorder);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access microphone. Please check your permissions.');
    }
  };

  const startRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.start();
      setIsRecording(true);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
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
            className={`message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            {msg.type === 'audio' ? (
              <audio controls src={msg.content} className="audio-player" />
            ) : (
              msg.content
            )}
          </div>
        ))}

        {/* Listening Animation */}
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
          className={`record-button ${isRecording ? 'recording' : ''}`}
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
