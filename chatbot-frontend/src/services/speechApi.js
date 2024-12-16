export async function streamAudioFromBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
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

    // Set up an AudioContext for playing audio
    const audioContext = new AudioContext();
    const source = audioContext.createBufferSource();
    const stream = response.body;

    const reader = stream.getReader();

    // Process the chunks
    async function processChunks() {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        console.log("Chunk received:", value);

        // Decode and play the received chunk
        const audioBuffer = await audioContext.decodeAudioData(value.buffer).catcg((err)=>{
          console.error("Audio decoding error:", err);
        });
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();
      }

      // Cleanup
      source.disconnect();
    }

    // Start processing chunks
    await processChunks();

    return;
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
    throw error;
  }
}



/*export async function sendAudioToBackend(audioBlob) {
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

export async function playAudioMessage(text) {
  const url = "http://127.0.0.1:8000/text-to-speech";
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) throw new Error("Failed to fetch audio response");

  const blob = await response.blob();
  const audioUrl = URL.createObjectURL(blob);
  console.log("Audio URL:", audioUrl);

  //automatically play the audio
  //uncomment this part to automatically play the audio
  const audio = new Audio(audioUrl);
  audio.play().catch(error => console.error("Audio playback error:", error));


  //no need for this as audio is currently playing automatically
  //return audioUrl;
}
  */
