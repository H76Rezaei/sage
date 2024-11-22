export async function sendToBackend(
  text,
  onChunk,
  isTextToSpeech = false,
  audioBlob = null
) {
  try {
    let url;
    let options;

    // If audioBlob exists, send audio file to server for voice-to-text conversion
    if (audioBlob) {
      url = "http://127.0.0.1:8000/voice-to-text";
      const formData = new FormData();
      formData.append("audio", audioBlob, "audio.wav"); // Add audio to FormData
      options = {
        method: "POST",
        body: formData, // Send audio as POST body
      };
    } else {
      // Otherwise, send message to the server for conversation
      url = "http://127.0.0.1:8000/conversation";
      options = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: text }), // Send the message as JSON
      };
    }
    console.log("Sending data to:", url);
    const response = await fetch(url, options); // Send request to the server

    if (!response.ok) {
      throw new Error("Network response was not ok"); // Handle network error
    }

    // If it's text-to-speech, play the audio response
    if (isTextToSpeech) {
      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.play(); // Play the audio
      return;
    }

    // If the message is text, handle the response and stream data
    if (text) {
      const data = await response.json(); // Get the JSON response
      onChunk({ text: data.text, isFinal: true }); // Pass the text to the parent function
      return;
    }
  } catch (error) {
    console.error("Error communicating with backend:", error); // Handle errors during communication
    return {
      response: "I'm having trouble responding right now.", // Default error response
    };
  }
}

export default sendToBackend;
