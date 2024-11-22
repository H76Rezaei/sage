export async function sendConversation(message, onChunk) {
    const url = "http://127.0.0.1:8000/conversation";
    const options = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    };
  
    const response = await fetch(url, options);
    if (!response.ok) throw new Error("Failed to connect to conversation endpoint");
  
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
  
      const chunk = new TextDecoder().decode(value);
      const lines = chunk.split("\n").filter((line) => line.trim().startsWith("data:"));
      for (const line of lines) {
        const data = JSON.parse(line.slice(5).trim());
        onChunk({ text: data.response, isFinal: data.is_final });
      }
    }
  }

export default sendConversation;