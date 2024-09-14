document.addEventListener("DOMContentLoaded", () => {
    let username = '';

    // Prompt for a username before joining the chat
    while (!username) {
        username = prompt("Please enter your username:");
    }

    // Connect to the chat room using the entered username
    const socket = io.connect('http://localhost:5000');
    const room = document.getElementById('room').value; // Assume the event room ID is in a hidden input field
    const messageInput = document.getElementById('messageInput');
    const messageForm = document.getElementById('messageForm');
    const messagesList = document.getElementById('messagesList');

    // Emit the join event with username and room info
    socket.emit('join', { username: username, room: room });

    // Handle message sending
    messageForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message = messageInput.value;

        // Send the message along with username
        if (message) {
            socket.emit('send_message', { username: username, message: message, room: room });
            messageInput.value = ''; // Clear the input after sending
        }
    });

    // Display received messages
    socket.on('message', function (data) {
        const messageElement = document.createElement('li');
        messageElement.textContent = `${data.username}: ${data.message}`;
        messagesList.appendChild(messageElement);
    });

    // Update the participants list (if needed)
    socket.on('update_participants', function (data) {
        const participantsList = document.getElementById('participantsList');
        participantsList.innerHTML = ''; // Clear the list
        data.participants.forEach(function (participant) {
            const participantElement = document.createElement('li');
            participantElement.textContent = participant.username;
            participantsList.appendChild(participantElement);
        });
    });
});
