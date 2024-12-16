import React, { useState } from 'react';
import MainPage from './components/MainPage';
import TextChat from './components/TextChat';
import VoiceChat from './components/VoiceChat';
import VoiceHistory from './components/VoiceHistory';
import { sendConversation } from "./services/textApi";
import { streamAudioFromBackend } from "./services/speechApi";
// Replace all instances of `sendAudioToBackend` and `playAudioMessage` with `streamAudioFromBackend` if applicable.

//import { sendAudioToBackend, playAudioMessage } from "./services/speechApi";

function App() {
    const [selectedOption, setSelectedOption] = useState('main');
    const [chatHistory, setChatHistory] = useState([]);

    const saveToHistory = (message) => {
        const updatedHistory = [...chatHistory, message];
        setChatHistory(updatedHistory);
        localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));
    };

    const handleSelectOption = (option) => {
        if (option === 'stop' || option === 'voiceHistory') {
            setSelectedOption('voiceHistory');
        } else {
            setSelectedOption(option);
        }
    };

    const renderContent = () => {
        if (selectedOption === 'text') {
            return (
                <TextChat 
                    onSelectOption={handleSelectOption} 
                    sendConversation={sendConversation} 
                    saveToHistory={saveToHistory} 
                />
            );
        }
        if (selectedOption === 'voice') {
            return (
                <VoiceChat 
                    key={selectedOption} // Force unmount when switching views
                    onSelectOption={handleSelectOption} 
                    streamAudioFromBackend={streamAudioFromBackend} 
                    //playAudioMessage={playAudioMessage} 
                    saveToHistory={saveToHistory}
                    setChatHistory={setChatHistory}
                />
            );
        }
        if (selectedOption === 'voiceHistory') {
            return (
                <VoiceHistory 
                    onSelectOption={handleSelectOption} 
                    chatHistory={chatHistory} 
                />
            );
        }
        return <MainPage onSelectOption={handleSelectOption} />;
    };

    return <div className="app-container">{renderContent()}</div>;
}

export default App;
