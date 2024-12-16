export async function streamAudioFromBackend(audioBlob) {
  //streaming
  //const url = "http://127.0.0.1:8000/conversation-audio-stream";

  //no streaming
  const url = "http://127.0.0.1:8000/conversation-audio";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  try {
    const response = await fetch(url, { method: "POST", body: formData });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to stream audio: ${response.statusText} - ${errorText}`
      );
    }

    // Get the response as a blob
    const audioData = await response.blob();
    
    // Create an audio element
    const audio = new Audio(URL.createObjectURL(audioData));

    // Clean up the object URL when done
    audio.onended = () => {
      URL.revokeObjectURL(audio.src);
    };

    return audio;
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
    throw error;
  }
}