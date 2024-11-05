const { createServer } = require('http');
const next = require('next');
const { Server: SocketIOServer } = require('socket.io');
const ClientIO = require('socket.io-client');


const dev = process.env.NODE_ENV !== 'production';
const hostname = '127.0.0.1';
const port = 5173;
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();


app.prepare().then(() => {
  const httpServer = createServer((req, res) => {
    handle(req, res);
  });

  const io = new SocketIOServer(httpServer, {
    cors: {
      origin: "*",
    },
  });

  // Connect to Flask backend only when there are clients connected
  let activeClients = 0;
  let flaskSocket;

  io.on('connection', (clientSocket) => {
    console.log('Client connected to Next.js server');
    activeClients += 1;

    console.log(`activeClients on connect: ${activeClients}`)

    // Establish a connection to Flask only if this is the first client
    if (activeClients === 1) {
      const backendUrl = process.env.NODE_ENV === 'development'
        ? 'http://127.0.0.1:5001'
        : 'http://backend.konduktor-dashboard.svc.cluster.local:5001';

      flaskSocket = ClientIO(backendUrl);

      flaskSocket.on('log_data', (data) => {
        io.emit('log_data', data); // Broadcast to all connected clients
        console.log(`activeClients during log_data: ${activeClients}`)
      });

      // Receive updated namespaces from the client (forward to Flask)
      clientSocket.on('update_namespaces', (namespaces) => {
        flaskSocket.emit('update_namespaces', namespaces);  // Send to Flask
        console.log(`activeClients during update_namespaces: ${activeClients}`)
      });

      console.log('Connected to Flask backend');
    }

    clientSocket.on('disconnect', () => {
      activeClients -= 1;
      console.log('Client disconnected from Next.js server');
      console.log(`activeClients after disconnect: ${activeClients}`)

      // Disconnect from Flask when no clients are connected
      if (activeClients === 0 && flaskSocket) {
        flaskSocket.disconnect();
        flaskSocket = null;
        console.log('Disconnected from Flask backend');
      }
    });
  });

  httpServer.listen(port, () => {
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});
