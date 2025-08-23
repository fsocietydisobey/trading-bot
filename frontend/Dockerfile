# dockerfile
# frontend/Dockerfile (production multi-stage)
FROM node:20 AS build
WORKDIR /app
COPY frontend-app/package*.json ./
RUN npm ci || npm install
COPY frontend-app/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]