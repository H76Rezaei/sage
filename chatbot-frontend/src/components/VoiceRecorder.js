import React, { useState } from 'react';
import { FaMicrophone } from 'react-icons/fa';  // Importing microphone icon from react-icons

function VoiceRecorder() {
    const [isRecording, setIsRecording] = useState(false);

    const handleRecord = () => {
        setIsRecording(!isRecording);
        // You can add logic here to start/stop actual recording
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