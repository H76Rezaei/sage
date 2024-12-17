export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

  // More sophisticated playback queue
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
    let headerCount = 0;
    let lastHeaderPosition = -1;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (value.byteLength > 0) {
        // More sophisticated WAV header detection
        const isWavHeader = (
          value[0] === 82 &&   // R
          value[1] === 73 &&   // I
          value[2] === 70 &&   // F
          value[3] === 70      // F
        );

        if (isWavHeader) {
          headerCount++;
          
          // If this is not the first header, process the previous chunk
          if (headerCount > 1 && currentChunk) {
            console.log(`Processing chunk before header #${headerCount}`);
            const chunkBlob = new Blob([currentChunk], { type: "audio/wav" });
            playbackQueue.push(chunkBlob);
            
            if (!isPlaying) {
              playNextChunk();
            }
          }

          // Reset current chunk to new WAV header
          currentChunk = value;
          lastHeaderPosition = chunkCounter;
        } else {
          // Append to current chunk if it exists
          if (currentChunk) {
            const combinedChunk = new Uint8Array([...currentChunk, ...value]);
            currentChunk = combinedChunk;
          } else {
            console.warn(`Received non-header chunk without preceding header at chunk ${chunkCounter}`);
            continue;
          }
        }

        // Debug logging
        console.log(`Chunk ${chunkCounter++}:`, {
          byteLength: value.byteLength,
          isWavHeader: isWavHeader,
          headerCount: headerCount
        });
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
    console.log(`Total headers found: ${headerCount}`);
    console.log(`Total chunks processed: ${chunkCounter}`);
  } catch (error) {
    console.error("Error streaming audio from backend:", error);
  }
}