# Use Node.js LTS version as base image
FROM node:20-slim

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (if exists)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all files
COPY . .

# Create empty files if they don't exist
RUN touch wallets.txt proxies.txt

# Set environment variables
ENV NODE_ENV=production

# Command to run the application
CMD ["node", "kiteai_bot.js"] 