//Displays the chat history on the screen using "messages" state
import React from 'react';

const ChatBox = ({ messages, loading }) => {
    return (
        <div className="chat-box">
            {messages.map((message, index) => (
                <div key={index} className={`message ${message.type}`}>
                    <div className="message-text">{message.text}</div>
                </div>
            ))}
            {loading && <div className="loading">Sage is typing...</div>}
        </div>
    );
};
export default ChatBox;
