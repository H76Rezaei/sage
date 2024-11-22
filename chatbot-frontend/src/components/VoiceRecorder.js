import React, { useState, useRef } from "react";
import { FaMicrophone } from "react-icons/fa";
import sendToBackend from "./services/api";

function VoiceRecorder({ onSendMessage }) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const mediaRecorderRef = useRef(null); // To hold the media recorder instance
  const audioStreamRef = useRef(null); // To hold the audio stream instance

  const handleRecord = async () => {
    if (isRecording) {
      setIsRecording(false);

      mediaRecorderRef.current.stop();
    } else {
      setIsRecording(true);

      try {
        // Access user's microphone
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

  // Function to send audio to backend once recording is stopped
  const sendAudioToBackend = async () => {
    if (audioBlob) {
      try {
        await sendToBackend(
          null,
          (data) => {
            if (data.isFinal) {
              onSendMessage(data.text);
            }
          },
          false,
          audioBlob
        );
      } catch (error) {
        console.error("Error processing audio:", error);
      }
    }
  };

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
