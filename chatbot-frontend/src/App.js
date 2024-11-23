import React, { useState } from 'react';
import MainPage from './components/MainPage';
import TextChat from './components/TextChat';
import VoiceChat from './components/VoiceChat';
import { sendConversation } from "./services/textApi";
import { sendAudioToBackend, playAudioMessage } from "./services/speechApi";

function App() {
    const [selectedOption, setSelectedOption] = useState(null);
    const [chatHistory, setChatHistory] = useState([]);

    const saveToHistory = (message) => {
        const updatedHistory = [...chatHistory, message];
        setChatHistory(updatedHistory);
        localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
    };
    const renderContent = () => {
        if (selectedOption === 'text') {
            //return <TextChat onSelectOption={setSelectedOption} />;
            return <TextChat onSelectOption={setSelectedOption} sendConversation={sendConversation}
            saveToHistory={saveToHistory} />;
        }
        if (selectedOption === 'voice') {
            return (
                <VoiceChat 
                    onSelectOption={setSelectedOption} 
                    sendAudioToBackend={sendAudioToBackend} 
                    playAudioMessage={playAudioMessage} 
                    saveToHistory={saveToHistory}
                />
            );
        }
        return <MainPage onSelectOption={setSelectedOption} />;
    };



    return <div className="app-container">{renderContent()}</div>;
}

export default App;
