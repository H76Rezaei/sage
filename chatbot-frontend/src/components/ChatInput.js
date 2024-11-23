import React, { useState } from 'react';
import VoiceRecorder from './VoiceRecorder';  // Import the VoiceRecorder component

function ChatInput({ onSendMessage }) {
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim()) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <div className="chat-footer">
            {/* Place VoiceRecorder next to the input field */}
            <VoiceRecorder />
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