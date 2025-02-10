export async function sendConversation(message, onChunk) {
  const token = localStorage.getItem("access_token") || "";
  const url = "http://127.0.0.1:8000/conversation";
  const options = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  };

  try {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (line.trim().startsWith("data:")) {
          try {
            const data = JSON.parse(line.slice(5).trim());

            console.log("Received chunk:", data);

            if (data.response) {
              onChunk(data);
            }
          } catch (parseError) {
            console.error("Error parsing chunk:", parseError);
          }
        }
      }
    }

    onChunk({ response: "", is_final: true });
  } catch (error) {
    console.error("Error in sendConversation:", error);
    throw error;
  }
}
