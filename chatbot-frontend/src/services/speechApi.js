export async function sendAudioToBackend(audioBlob) {
    const url = "http://127.0.0.1:8000/voice-to-text";
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");
  
    const response = await fetch(url, { method: "POST", body: formData });
    if (!response.ok) throw new Error("Failed to process audio");
  
    const data = await response.json();
    return data.text;
  }
  
  export async function playAudioMessage(text) {
    const url = "http://127.0.0.1:8000/text-to-speech";
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
  
    const blob = await response.blob();
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    audio.play();
  }
  
  