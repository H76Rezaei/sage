export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  try {
    const response = await fetch(url, { method: "POST", body: formData });
    if (!response.body) throw new Error("No readable stream in response");

    const reader = response.body.getReader();
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (value) {
        console.log("Received audio chunk:", value);

        try {
          // Decode and play each chunk
          const audioData = await audioContext.decodeAudioData(value.buffer);
          playDecodedChunk(audioData, audioContext);
        } catch (decodeError) {
          console.error("Error decoding audio chunk:", decodeError);
        }
      }
    }
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
    throw error;
  }
}

function playDecodedChunk(audioBuffer, audioContext) {
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start();
  console.log("Playing chunk...");
  source.onended = () => console.log("Chunk playback finished.");
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

/*
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
  */