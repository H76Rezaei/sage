//Displays the chat history on the screen using "messages" state
import React from 'react';

function ChatBox({ messages, loading }) {
    return (
        <div className="chat-box">
            {messages.map((msg, index) => (
                <div key={index} className={`message ${msg.type}`}>
                    {msg.type === 'bot' ? (
                        <>
                            <div>{msg.text}</div>
                            <div className="emotion-label">Emotion: {msg.emotion}</div>
                        </>
                    ) : (
                        <div>{msg.text}</div>
                    )}
                </div>
            ))}
            {loading && (
                <div className="loading-indicator">
                    <span>Loading...</span>
                </div>
            )}
        </div>
    );
}

export default ChatBox;
