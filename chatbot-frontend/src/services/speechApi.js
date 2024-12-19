export async function sendAudioToBackend(audioBlob) {
  const url = "http://127.0.0.1:8000/conversation-audio-stream";
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.wav");

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
    let accumulatedData = new Uint8Array();
    let chunkCounter = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (value && value.byteLength > 0) {
        const combinedData = new Uint8Array(accumulatedData.length + value.length);
        combinedData.set(accumulatedData, 0);
        combinedData.set(value, accumulatedData.length);
        accumulatedData = combinedData;

        let startIndex = 0;
        while (startIndex < accumulatedData.length) {
          const isWavHeader =
            accumulatedData[startIndex] === 82 && // R
            accumulatedData[startIndex + 1] === 73 && // I
            accumulatedData[startIndex + 2] === 70 && // F
            accumulatedData[startIndex + 3] === 70; // F

          if (isWavHeader) {
            let dataLength = accumulatedData.length - startIndex;
            if (dataLength >= 8) { // Check for minimum RIFF header size
              const riffChunkSize = new DataView(accumulatedData.buffer, startIndex + 4, 4).getUint32(0, true) + 8; // Read chunk size
              if (dataLength >= riffChunkSize) {
                const wavData = accumulatedData.subarray(startIndex, startIndex + riffChunkSize);
                const chunkBlob = new Blob([wavData], { type: "audio/wav" });
                playbackQueue.push(chunkBlob);
                if (!isPlaying) playNextChunk();

                startIndex += riffChunkSize;
                continue; // Process next WAV in accumulated data
              }
            }
          }
          break; // No more complete WAV files found
        }
        accumulatedData = accumulatedData.subarray(startIndex); // Remove processed data
        console.log(`Chunk ${chunkCounter++}:`, { byteLength: value.byteLength });
      }
    }

    console.log("All audio chunks processed.");
  } catch (error) {
    console.error("Error streaming audio:", error);
  }
}