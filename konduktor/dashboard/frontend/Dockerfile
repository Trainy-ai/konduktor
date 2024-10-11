# Use the official Node.js 18 slim image
FROM node:18-slim
# Set the working directory
WORKDIR /app
# Copy package.json and package-lock.json (if available)
COPY package*.json ./
# Install dependencies
RUN npm install
# Copy the rest of the application files
COPY . .
# Build the Next.js app for production
RUN npm run build
# Expose the custom port
EXPOSE 5173
# Start the Next.js app with the custom port
CMD ["npm", "run", "start"]
