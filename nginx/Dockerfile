FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create static files directory
RUN mkdir -p /app/static

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
