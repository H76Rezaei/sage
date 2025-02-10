export async function sendAudioToBackend(audioBlob) {
  
  const token = localStorage.getItem("access_token") || "";
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
    return response;
  } catch (error) {
    console.error("Error sending audio to backend:", error);
    throw error;
  }
}
