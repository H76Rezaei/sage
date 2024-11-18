import React, { useState, useEffect } from 'react';
import ChatBox from './components/ChatBox';
import ChatInput from './components/ChatInput';
import ChatHistory from './components/ChatHistory';
import sendToBackend from './services/api';
import './App.css';

function App() {
  /*
  messages is a useState
  loading is a useState
  */
    const [messages, setMessages] = useState([]); //Store the chat History in an array of "message" objects
    const [loading, setLoading] = useState(false); //Loading state

  /*
  useEffect is a "Hook"

  - Fetches the stored chat history from localStorage
  - Adds the fetched history to the state "messages"
  */
    useEffect(() => {
        const storedHistory = JSON.parse(localStorage.getItem('chatHistory')) || [];
        setMessages(storedHistory);
    }, []);

    /*
    handleSendMessage is an Event Handler
    */ 
    const handleSendMessage = async (text) => {
        const userMessage = { type: 'user', text }; //create new user message object
        setMessages((prev) => [...prev, userMessage]); //append user message to the "messages" state 
        saveToHistory(userMessage); //save the user message to localStorage 

        //Loading indicator
        setLoading(true); // Show loading indicator


        //  backend response for now
        try {
            const data = await sendToBackend(text);
            console.log('Full response data:', data);
            console.log('Emotion Analysis:', data.emotion); 
            
            //removing emotion from bot response
            //const botMessage = { type: 'bot', text: data.response, emotion: data.emotion };

            const botMessage = { type: 'bot', text: data.response };
            setMessages((prev) => [...prev, botMessage]);
            saveToHistory(botMessage);
        } finally {
            setLoading(false);
        }
    };

    /*
    Clears the chat history
    */
    const clearChatHistory = () => {
        localStorage.removeItem('chatHistory'); //remove chat history from localStorage
        setMessages([]); //clear the "messages" state
    };

    //Save chat history
    const saveToHistory = (message) => {
        const history = JSON.parse(localStorage.getItem('chatHistory')) || [];
        history.push(message);
        localStorage.setItem('chatHistory', JSON.stringify(history));
    };

    return (
        <div className="chat-container">
            <header className="chat-header">
                <h1>Chatbot</h1>
                <button onClick={clearChatHistory}>Clear History</button>
            </header>
            <ChatBox messages={messages} loading={loading} />
            <ChatInput onSendMessage={handleSendMessage} />
        </div>
    );
}

export default App;
