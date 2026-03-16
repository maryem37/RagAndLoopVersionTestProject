FROM maven:3.9-eclipse-temurin-17

WORKDIR /tests

# Install utilities
RUN apt-get update && \
    apt-get install -y curl wget && \
    rm -rf /var/lib/apt/lists/*

# Copy wait-for-it script
COPY wait-for-it.sh /usr/local/bin/wait-for-it
RUN chmod +x /usr/local/bin/wait-for-it

# Pre-download Maven dependencies (cache layer)
COPY pom.xml .
RUN mvn dependency:go-offline -B || true

CMD ["mvn", "clean", "test"]