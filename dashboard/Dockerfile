FROM node:10.15 as build-deps
WORKDIR /dashboard
COPY ./dashboard/package.json ./dashboard/yarn.lock ./
RUN yarn
COPY ./dashboard/. ./
RUN yarn build
FROM nginx:1.12-alpine
COPY --from=build-deps /dashboard/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
