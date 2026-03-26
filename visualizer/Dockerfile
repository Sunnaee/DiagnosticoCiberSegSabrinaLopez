FROM node:18-alpine
WORKDIR /app
COPY package.json /app/package.json
RUN npm install --production
COPY server.js /app/server.js
COPY public /app/public
EXPOSE 4000
CMD ["node","server.js"]