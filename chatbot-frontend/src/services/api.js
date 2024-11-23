export async function sendToBackend(message, onChunk) {
  try {
    const response = await fetch('http://127.0.0.1:8000/conversation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const reader = response.body.getReader();
    let accumulatedText = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      // Convert the chunk to text and parse the JSON
      const chunk = new TextDecoder().decode(value);
      const lines = chunk.split('\n').filter(line => line.trim().startsWith('data:'));
      
      for (const line of lines) {
        try {
          // Remove 'data: ' prefix
          const jsonStr = line.slice(6).trim();
          const data = JSON.parse(jsonStr);
          accumulatedText = data.response;
          
          // Call the callback with the current state
          onChunk({
            text: accumulatedText,
            isFinal: data.is_final
          });
          
        } catch (e) {
          console.error('Error parsing chunk:', e);
        }
      }
    }

    return { 
      response: accumulatedText,
    };
  } catch (error) {
    console.error('Error communicating with backend:', error);
    return { 
      response: "I'm having trouble responding right now.",
    };
  }
}

export default sendToBackend;