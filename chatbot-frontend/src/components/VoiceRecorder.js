import React, { useState, useRef } from "react";
import { FaMicrophone } from "react-icons/fa";
import { sendAudioToBackend } from "../services/speechApi";

function VoiceRecorder({ onSendMessage }) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunks = useRef([]);

  const handleRecord = async () => {
    if (isRecording) {
      setIsRecording(false);
      mediaRecorderRef.current.stop();
    } else {
      try {
        setIsRecording(true);
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorderRef.current = new MediaRecorder(stream);

        mediaRecorderRef.current.ondataavailable = (event) => {
          audioChunks.current.push(event.data);
        };

        mediaRecorderRef.current.onstop = async () => {
          const audioBlob = new Blob(audioChunks.current, { type: "audio/wav" });
          audioChunks.current = [];
          const text = await sendAudioToBackend(audioBlob);
          if (text) onSendMessage(text);
        };

        mediaRecorderRef.current.start();
      } catch (err) {
        console.error("Error accessing microphone:", err);
        setIsRecording(false);
      }
    }
  };

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
