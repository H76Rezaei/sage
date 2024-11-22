import React, { useState, useRef } from "react";
import { FaMicrophone } from "react-icons/fa";
import sendToBackend from "../services/api.js";

function VoiceRecorder({ onSendMessage }) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioStreamRef = useRef(null);

  // Start or stop the recording
  const handleRecord = async () => {
    if (isRecording) {
      setIsRecording(false);
      mediaRecorderRef.current.stop();
    } else {
      setIsRecording(true);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        audioStreamRef.current = stream;
        const mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (e) => {
          setAudioBlob(e.data);
        };

        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.start();
      } catch (err) {
        console.error("Error accessing the microphone:", err);
        setIsRecording(false);
      }
    }
  };
  // Send the audio file to the backend after stopping the recording
  const sendAudioToBackend = async () => {
    if (audioBlob) {
      const formData = new FormData();
      formData.append("audio", audioBlob, "audio.wav");

      try {
        // Send the audio file to the server for processing
        const response = await sendToBackend(formData);

        // If a response is received from the server
        if (response && response.text) {
          onSendMessage(response.text);
        }
      } catch (error) {
        console.error("Error processing audio:", error);
      }
    }
  };

  // If recording has stopped and the audio file exists, send it to the backend
  if (!isRecording && audioBlob) {
    sendAudioToBackend();
  }

  return (
    <button
      className="voice-recorder-button"
      onClick={handleRecord}
      title={isRecording ? "Stop Recording" : "Start Recording"}
    >
      <FaMicrophone size={24} color={isRecording ? "red" : "black"} />
    </button>
  );
}

export default VoiceRecorder;
