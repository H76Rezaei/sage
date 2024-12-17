export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  // Playback queue
  const playbackQueue = [];
  let isPlaying = false;
  let currentChunk = null;

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
      URL.revokeObjectURL(audioUrl);
      playNextChunk();
    });

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      playNextChunk();
    };
  };

  try {
    const response = await fetch(url, { method: "POST", body: formData });
    if (!response.body) throw new Error("No readable stream in response");

    const reader = response.body.getReader();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (value.byteLength > 0) {
        // Check if this is the start of a new WAV file
        const isWavHeader = (
          value[0] === 82 &&   // R
          value[1] === 73 &&   // I
          value[2] === 70 &&   // F
          value[3] === 70      // F
        );

        console.log("Received chunk:", {
          byteLength: value.byteLength,
          firstBytes: Array.from(value.slice(0, 20)),
          isWavHeader: isWavHeader
        });

        if (isWavHeader) {
          // Start of a new WAV file, process previous chunk if exists
          if (currentChunk) {
            const chunkBlob = new Blob([currentChunk], { type: "audio/wav" });
            playbackQueue.push(chunkBlob);
            
            if (!isPlaying) {
              playNextChunk();
            }
          }
          
          // Reset current chunk to new WAV file
          currentChunk = value;
        } else if (currentChunk) {
          // Append to existing chunk
          const combinedChunk = new Uint8Array([...currentChunk, ...value]);
          currentChunk = combinedChunk;
        }
      }
    }

    // Process final chunk
    if (currentChunk) {
      const chunkBlob = new Blob([currentChunk], { type: "audio/wav" });
      playbackQueue.push(chunkBlob);
      
      if (!isPlaying) {
        playNextChunk();
      }
    }

    console.log("All audio chunks have been processed.");
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
  }
}