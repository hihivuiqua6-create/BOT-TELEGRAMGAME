FROM node:20-bookworm-slim

# Dùng khi muốn deploy bằng Docker. Cài build tools để better-sqlite3 build không lỗi.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3 make g++ ca-certificates php-cli php-mbstring php-xml php-curl php-zip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY . .

ENV NODE_ENV=production
ENV PHP_BIN=php
EXPOSE 3000
CMD ["npm", "start"]
