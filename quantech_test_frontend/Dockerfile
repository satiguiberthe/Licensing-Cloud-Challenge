# Stage 1: Build the Angular application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY src/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src/ .

# Build the application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder /app/dist/src/browser /usr/share/nginx/html

# Rename index.csr.html to index.html for Angular SSR
RUN if [ -f /usr/share/nginx/html/index.csr.html ]; then \
      mv /usr/share/nginx/html/index.csr.html /usr/share/nginx/html/index.html; \
    fi

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
