//Handles user input
//Triggers handleSendMessage function
import React, { useState } from 'react';

function ChatInput({ onSendMessage }) {
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim()) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <div className="chat-input-container">
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message..."
            />
            <button onClick={handleSend}>Send</button>
        </div>
        
    );
}

export default ChatInput;
