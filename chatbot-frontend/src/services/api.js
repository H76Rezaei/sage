export async function sendToBackend(
  message,
  onChunk,
  isTextToSpeech = false,
  audioBlob = null
) {
  try {
    let url; // URL for the request
    let options; // Request options

    // If the request is for voice-to-text (converting audio to text)
    if (audioBlob) {
      url = "http://127.0.0.1:8000/voice-to-text";
      const formData = new FormData();
      formData.append("audio", audioBlob, "audio.wav");

      options = {
        method: "POST",
        body: formData,
      };
    }
    // If the request is for text-to-speech (converting text to audio)
    else if (isTextToSpeech) {
      url = "http://127.0.0.1:8000/text-to-speech";
      options = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: message }),
      };
    }
    // If it's a conversation with the model (text-based)
    else {
      url = "http://127.0.0.1:8000/conversation";
      options = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      };
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    // If the request is for text-to-speech, handle the audio playback
    if (isTextToSpeech) {
      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.play();
      return;
    }

    // If the request is for voice-to-text, process the response as text
    if (audioBlob) {
      const data = await response.json();
      onChunk({ text: data.text, isFinal: true });
      return;
    }

    // If it's a regular conversation, process the streamed response
    const reader = response.body.getReader();
    let accumulatedText = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      const chunk = new TextDecoder().decode(value);
      const lines = chunk
        .split("\n")
        .filter((line) => line.trim().startsWith("data:"));

      for (const line of lines) {
        try {
          const jsonStr = line.slice(6).trim();
          const data = JSON.parse(jsonStr);
          accumulatedText = data.response;

          onChunk({
            text: accumulatedText,
            isFinal: data.is_final,
          });
        } catch (e) {
          console.error("Error parsing chunk:", e);
        }
      }
    }

    return { response: accumulatedText };
  } catch (error) {
    console.error("Error communicating with backend:", error);
    return {
      response: "I'm having trouble responding right now.",
    };
  }
}

export default sendToBackend;
