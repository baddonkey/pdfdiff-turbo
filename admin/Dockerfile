FROM node:20-alpine AS build
WORKDIR /app
COPY package.json /app/package.json
COPY angular.json /app/angular.json
COPY tsconfig.json /app/tsconfig.json
COPY tsconfig.app.json /app/tsconfig.app.json
RUN npm install
COPY src /app/src
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist/pdfdiff-admin/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
