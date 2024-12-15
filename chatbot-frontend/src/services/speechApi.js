export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/voice-to-text";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  try {
    const response = await fetch(url, { method: "POST", body: formData });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to process audio: ${response.statusText} - ${errorText}`
      );
    }

    const data = await response.json();
    console.log("Received text from backend:", data.text);
    return data.text;
  } catch (error) {
    console.error("Error:", error);
    alert(`Error: ${error.message}`);
    throw error;
  }
}

export async function playAudioMessage(text, gender = "male") {
  const url = "http://127.0.0.1:8000/text-to-speech";

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, gender }),
    });

    if (!response.ok) throw new Error("Failed to fetch audio response");

    const blob = await response.blob();
    const audioUrl = URL.createObjectURL(blob);
    console.log("Audio URL:", audioUrl);

    const audio = new Audio(audioUrl);
    audio
      .play()
      .catch((error) => console.error("Audio playback error:", error));
  } catch (error) {
    console.error("Failed to play audio message:", error);
  }
}
