export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  // Playback queue with better chunk management
  const playbackQueue = [];
  let isPlaying = false;
  let currentChunk = null;
  let chunkCounter = 0;

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
    let previousChunkWasHeader = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (value.byteLength > 0) {
        // Improved WAV header detection
        const isWavHeader = (
          value[0] === 82 &&   // R
          value[1] === 73 &&   // I
          value[2] === 70 &&   // F
          value[3] === 70      // F
        );

        // Debug logging with chunk counter
        console.log(`Chunk ${chunkCounter++}:`, {
          byteLength: value.byteLength,
          isWavHeader: isWavHeader,
          previousChunkWasHeader: previousChunkWasHeader
        });

        if (isWavHeader) {
          // If previous chunk was a header, this is a new audio segment
          if (previousChunkWasHeader && currentChunk) {
            console.warn("Multiple WAV headers detected. Finalizing previous chunk.");
            const finalChunkBlob = new Blob([currentChunk], { type: "audio/wav" });
            playbackQueue.push(finalChunkBlob);
          }
          
          // Start a new chunk with this WAV header
          currentChunk = value;
          previousChunkWasHeader = true;
        } else {
          // Non-header chunk: append to current chunk
          if (currentChunk) {
            const combinedChunk = new Uint8Array([...currentChunk, ...value]);
            currentChunk = combinedChunk;
            previousChunkWasHeader = false;
          } else {
            console.warn("Received non-header chunk without a preceding header");
            continue;
          }
        }

        // Queue for playback if chunk is substantial
        if (!isWavHeader && currentChunk && currentChunk.byteLength > 1024) {
          const chunkBlob = new Blob([currentChunk], { type: "audio/wav" });
          playbackQueue.push(chunkBlob);
          
          if (!isPlaying) {
            playNextChunk();
          }
        }
      }
    }

    // Process final chunk
    if (currentChunk) {
      const finalChunkBlob = new Blob([currentChunk], { type: "audio/wav" });
      playbackQueue.push(finalChunkBlob);
      
      if (!isPlaying) {
        playNextChunk();
      }
    }

    console.log("All audio chunks have been processed.");
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
  }
}