export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  try {
      const response = await fetch(url, { method: "POST", body: formData });
      return response;
  } catch (error) {
      console.error("Error sending audio to backend:", error);
      throw error;
  }
}