document.addEventListener("DOMContentLoaded", () => {
    let username = '';

    while (!username) {
        username = prompt("Please enter your username:");
    }

    const socket = io.connect('http://localhost:5000');
    const room = document.getElementById('room').value; 
    const messageInput = document.getElementById('messageInput');
    const messageForm = document.getElementById('messageForm');
    const messagesList = document.getElementById('messagesList');

    socket.emit('join', { username: username, room: room });

    messageForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const message = messageInput.value;

        if (message) {
            socket.emit('send_message', { username: username, message: message, room: room });
            messageInput.value = ''; 
        }
    });

    socket.on('message', function (data) {
        const messageElement = document.createElement('li');
        messageElement.textContent = `${data.username}: ${data.message}`;
        messagesList.appendChild(messageElement);
    });

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
