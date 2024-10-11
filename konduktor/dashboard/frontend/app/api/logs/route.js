import { Server } from 'socket.io';


const SocketHandler = (req, res) => {
    if (res.socket.server.io) {
        console.log('Socket is already running');
        res.end();
        return;
    }

    const io = new Server(res.socket.server);
    res.socket.server.io = io;

    io.on('connection', socket => {
        console.log('New client connected');

        // Emit log data to the client
        socket.emit('log_data', { log: 'Initial log data' });

        socket.on('disconnect', () => {
            console.log('Client disconnected');
        });
    });

    res.end();
};

export default SocketHandler;
