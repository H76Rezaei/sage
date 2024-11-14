export async function sendToBackend(message) {
    try {
        const response = await fetch('http://127.0.0.1:5000/conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error communicating with backend:', error);
        return { response: "I'm having trouble responding right now.", emotion: "Neutral" };
    }
}
export default sendToBackend;