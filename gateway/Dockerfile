FROM golang:1.23-alpine AS build
WORKDIR /src
COPY proxy.go session.go native.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o /out/gateway proxy.go session.go native.go
FROM scratch
COPY --from=build /out/gateway /gateway
USER 65532:65532
ENTRYPOINT ["/gateway"]
