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
  let fastapiSocket;

  io.on('connection', (clientSocket) => {
    activeClients += 1;

    // Establish a connection to Flask only if this is the first client
    if (activeClients === 1) {
      const backendUrl = process.env.NODE_ENV === 'development'
        ? 'http://127.0.0.1:5001'
        : 'http://backend.konduktor-dashboard.svc.cluster.local:5001';

      fastapiSocket = ClientIO(backendUrl);

      fastapiSocket.on('log_data', (data) => {
        io.emit('log_data', data); // Broadcast to all connected clients
      });

      // Receive updated namespaces from the client (forward to Flask)
      clientSocket.on('update_namespaces', (namespaces) => {
        fastapiSocket.emit('update_namespaces', namespaces);  // Send to Flask
      });
    }

    clientSocket.on('disconnect', () => {
      activeClients -= 1;

      // Disconnect from Flask when no clients are connected
      if (activeClients === 0 && fastapiSocket) {
        fastapiSocket.disconnect();
        fastapiSocket = null;
      }
    });
  });

  httpServer.listen(port, () => {
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});
