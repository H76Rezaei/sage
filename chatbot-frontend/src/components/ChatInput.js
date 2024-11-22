import React, { useState } from "react";
import VoiceRecorder from "./VoiceRecorder";

function ChatInput({ onSendMessage, onSendAudioMessage }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput("");
    }
  };

  return (
    <div className="chat-footer">
      <VoiceRecorder onSendAudioMessage={onSendAudioMessage} />
      <div className="chat-input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
}

export default ChatInput;
