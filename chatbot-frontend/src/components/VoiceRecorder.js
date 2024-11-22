import React, { useState, useRef } from "react";
import { FaMicrophone } from "react-icons/fa";

function VoiceRecorder({ onSendAudioMessage }) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunks = useRef([]);
  const audioStreamRef = useRef(null);

  const handleRecord = async () => {
    if (isRecording) {
      setIsRecording(false);
      mediaRecorderRef.current.stop();
    } else {
      try {
        setIsRecording(true);
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioStreamRef.current = stream;
        mediaRecorderRef.current = new MediaRecorder(stream);

        mediaRecorderRef.current.ondataavailable = (event) => {
          audioChunks.current.push(event.data);
        };

        mediaRecorderRef.current.onstop = async () => {
          const audioBlob = new Blob(audioChunks.current, { type: "audio/wav" });
          audioChunks.current = [];
          if (audioStreamRef.current) {
            audioStreamRef.current.getTracks().forEach((track) => track.stop());
          }
          if (typeof onSendAudioMessage === "function") {
            await onSendAudioMessage(audioBlob);
          } else {
            console.error("onSendAudioMessage is not a valid function");
          }
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
