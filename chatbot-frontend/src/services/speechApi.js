export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  // Playback queue
  const playbackQueue = [];
  let isPlaying = false;

  const playNextChunk = () => {
    if (playbackQueue.length === 0) {
      isPlaying = false;
      return;
    }

    isPlaying = true;
    const audioBlob = playbackQueue.shift();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.play().catch(error => {
      console.error("Error playing audio chunk:", error);
      // Continue to next chunk even if this one fails
      URL.revokeObjectURL(audioUrl);
      playNextChunk();
    });

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      playNextChunk(); // Play the next chunk
    };
  };

  try {
    const response = await fetch(url, { method: "POST", body: formData });
    if (!response.body) throw new Error("No readable stream in response");

    const reader = response.body.getReader();
    const chunks = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (value.byteLength > 0) {
        // More comprehensive WAV header validation
        const isValidWav = (
          value[0] === 82 &&   // R
          value[1] === 73 &&   // I
          value[2] === 70 &&   // F
          value[3] === 70      // F
        );

        console.log("Received chunk:", {
          byteLength: value.byteLength,
          firstBytes: Array.from(value.slice(0, 20)),
          isValidWav: isValidWav
        });

        if (!isValidWav) {
          console.error("Invalid WAV chunk:", value.slice(0, 44));
          continue;
        }

        const chunkBlob = new Blob([value], { type: "audio/wav" });
        playbackQueue.push(chunkBlob);

        // Ensure playback starts for all queued chunks
        if (!isPlaying) {
          playNextChunk();
        }
      }
    }

    console.log("All audio chunks have been processed.");
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
  }
}