// used to host socket.io logs stuff in frontend server 
const { createServer } = require('http');
const next = require('next');
const { Server: SocketIOServer } = require('socket.io');
const ClientIO = require('socket.io-client'); // Client-side connection to Flask

const dev = process.env.NODE_ENV !== 'production';
const hostname = '127.0.0.1'; // or your production hostname
const port = 5173; // This is the Next.js port

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const httpServer = createServer((req, res) => {
    handle(req, res);
  });

  const io = new SocketIOServer(httpServer, {
    cors: {
      origin: "*", // Allow all origins (adjust in production if necessary)
    },
  });

  const backendUrl = process.env.NODE_ENV === 'development'
    ? 'http://127.0.0.1:5000' // Development API
    : 'http://backend.konduktor-dashboard.svc.cluster.local:5001'; // Production API

  // Connect to the Flask backend's Socket.IO
  const flaskSocket = ClientIO(backendUrl); // Flask backend URL

  // When Next.js gets a client connection
  io.on('connection', (clientSocket) => {
    console.log('Client connected to Next.js server');

    // Forward any data received from Flask to the connected client
    flaskSocket.on('log_data', (data) => {
      clientSocket.emit('log_data', data); // Forward logs to the client
    });

    // Receive updated namespaces from the client
    clientSocket.on('update_namespaces', (namespaces) => {
      console.log('Received namespaces from client:', namespaces);
      flaskSocket.emit('update_namespaces', namespaces);  // Send to Flask
    });

    clientSocket.on('disconnect', () => {
      console.log('Client disconnected from Next.js');
    });
  });

  httpServer.listen(port, () => {
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});
