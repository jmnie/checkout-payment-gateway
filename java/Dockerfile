FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /build
COPY java/gradle ./gradle
COPY java/gradlew java/build.gradle java/settings.gradle ./
COPY java/src/main ./src/main
COPY docs/openapi.json /docs/openapi.json
RUN chmod +x gradlew && ./gradlew bootJar --no-daemon

FROM eclipse-temurin:17-jre-jammy
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*     && useradd --uid 10001 --no-create-home gateway
WORKDIR /app
COPY --from=build /build/build/libs/payment-gateway.jar ./app.jar
USER 10001
EXPOSE 8090
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s CMD ["curl", "-fsS", "http://127.0.0.1:8090/health"]
ENTRYPOINT ["java", "-jar", "app.jar"]
