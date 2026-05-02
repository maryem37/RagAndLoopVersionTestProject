# Script to stop running Java services and restart them with JaCoCo agent monitoring
# This enables coverage data collection for the microservices

# Configuration
$JAVA_HOME = "C:\Program Files\Java\jdk-17"
$JAVA_EXE = "$JAVA_HOME\bin\java.exe"
$CONGE_PATH = "C:\Bureau\Bureau\microservices\conge\target\classes"
$DEMANDE_CONGE_PATH = "C:\Bureau\Bureau\microservices\DemandeConge\target\classes"
$JACOCO_AGENT = "D:\project_testRAG - Copie\jacocoagent.jar"
$OUTPUT_DIR = "D:\project_testRAG - Copie\output\jacoco"
$MAVEN_REPO = "$env:USERPROFILE\.m2\repository"

# Create output directory if it doesn't exist
if (-not (Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Path $OUTPUT_DIR -Force | Out-Null
    Write-Host "Created output directory: $OUTPUT_DIR"
}

# Step 1: Stop existing Java processes for the services
Write-Host "Step 1: Stopping existing services..."
Write-Host "  Killing process on port 9000 (Leave Service)..."
Get-Process java -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*CongeeApplication*"
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "  Killing process on port 9001 (Auth Service)..."
Get-Process java -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*DemandeCongeApplication*"
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "  Services stopped."

# Step 2: Verify JaCoCo agent exists
Write-Host "Step 2: Checking JaCoCo agent..."
if (-not (Test-Path $JACOCO_AGENT)) {
    Write-Host "ERROR: JaCoCo agent not found at: $JACOCO_AGENT"
    exit 1
}
Write-Host "  JaCoCo agent found: $JACOCO_AGENT"

# Step 3: Build the classpath for conge service
Write-Host "Step 3: Building classpath for Leave Service (conge)..."
$CONGE_CLASSPATH = @(
    "$CONGE_PATH",
    # Spring Boot dependencies
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-actuator\3.2.3\spring-boot-starter-actuator-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter\3.2.3\spring-boot-starter-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot\3.2.3\spring-boot-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-autoconfigure\3.2.3\spring-boot-autoconfigure-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-logging\3.2.3\spring-boot-starter-logging-3.2.3.jar",
    "$MAVEN_REPO\org\apache\logging\log4j\log4j-to-slf4j\2.21.1\log4j-to-slf4j-2.21.1.jar",
    "$MAVEN_REPO\org\apache\logging\log4j\log4j-api\2.21.1\log4j-api-2.21.1.jar",
    "$MAVEN_REPO\org\slf4j\jul-to-slf4j\2.0.12\jul-to-slf4j-2.0.12.jar",
    "$MAVEN_REPO\jakarta\annotation\jakarta.annotation-api\2.1.1\jakarta.annotation-api-2.1.1.jar",
    "$MAVEN_REPO\org\yaml\snakeyaml\2.2\snakeyaml-2.2.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-actuator-autoconfigure\3.2.3\spring-boot-actuator-autoconfigure-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-actuator\3.2.3\spring-boot-actuator-3.2.3.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\datatype\jackson-datatype-jsr310\2.15.4\jackson-datatype-jsr310-2.15.4.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-observation\1.12.3\micrometer-observation-1.12.3.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-commons\1.12.3\micrometer-commons-1.12.3.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-jakarta9\1.12.3\micrometer-jakarta9-1.12.3.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-core\1.12.3\micrometer-core-1.12.3.jar",
    "$MAVEN_REPO\org\hdrhistogram\HdrHistogram\2.1.12\HdrHistogram-2.1.12.jar",
    "$MAVEN_REPO\org\latencyutils\LatencyUtils\2.0.3\LatencyUtils-2.0.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-data-jpa\3.2.3\spring-boot-starter-data-jpa-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-aop\3.2.3\spring-boot-starter-aop-3.2.3.jar",
    "$MAVEN_REPO\org\aspectj\aspectjweaver\1.9.21\aspectjweaver-1.9.21.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-jdbc\3.2.3\spring-boot-starter-jdbc-3.2.3.jar",
    "$MAVEN_REPO\com\zaxxer\HikariCP\5.0.1\HikariCP-5.0.1.jar",
    "$MAVEN_REPO\org\springframework\spring-jdbc\6.1.4\spring-jdbc-6.1.4.jar",
    "$MAVEN_REPO\org\hibernate\orm\hibernate-core\6.4.4.Final\hibernate-core-6.4.4.Final.jar",
    "$MAVEN_REPO\jakarta\persistence\jakarta.persistence-api\3.1.0\jakarta.persistence-api-3.1.0.jar",
    "$MAVEN_REPO\jakarta\transaction\jakarta.transaction-api\2.0.1\jakarta.transaction-api-2.0.1.jar",
    "$MAVEN_REPO\org\jboss\logging\jboss-logging\3.5.3.Final\jboss-logging-3.5.3.Final.jar",
    "$MAVEN_REPO\org\hibernate\common\hibernate-commons-annotations\6.0.6.Final\hibernate-commons-annotations-6.0.6.Final.jar",
    "$MAVEN_REPO\io\smallrye\jandex\3.1.2\jandex-3.1.2.jar",
    "$MAVEN_REPO\com\fasterxml\classmate\1.6.0\classmate-1.6.0.jar",
    "$MAVEN_REPO\org\glassfish\jaxb\jaxb-runtime\4.0.4\jaxb-runtime-4.0.4.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-web\3.2.3\spring-boot-starter-web-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-json\3.2.3\spring-boot-starter-json-3.2.3.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\datatype\jackson-datatype-jdk8\2.15.4\jackson-datatype-jdk8-2.15.4.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\module\jackson-module-parameter-names\2.15.4\jackson-module-parameter-names-2.15.4.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-tomcat\3.2.3\spring-boot-starter-tomcat-3.2.3.jar",
    "$MAVEN_REPO\org\apache\tomcat\embed\tomcat-embed-core\10.1.19\tomcat-embed-core-10.1.19.jar",
    "$MAVEN_REPO\org\apache\tomcat\embed\tomcat-embed-el\10.1.19\tomcat-embed-el-10.1.19.jar",
    "$MAVEN_REPO\org\apache\tomcat\embed\tomcat-embed-websocket\10.1.19\tomcat-embed-websocket-10.1.19.jar",
    "$MAVEN_REPO\org\springframework\spring-web\6.1.4\spring-web-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-webmvc\6.1.4\spring-webmvc-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-expression\6.1.4\spring-expression-6.1.4.jar",
    "$MAVEN_REPO\com\mysql\mysql-connector-j\8.0.33\mysql-connector-j-8.0.33.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-security\3.2.3\spring-boot-starter-security-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\spring-aop\6.1.4\spring-aop-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-config\6.2.2\spring-security-config-6.2.2.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-core\6.2.2\spring-security-core-6.2.2.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-crypto\6.2.2\spring-security-crypto-6.2.2.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-web\6.2.2\spring-security-web-6.2.2.jar",
    "$MAVEN_REPO\io\jsonwebtoken\jjwt-api\0.11.5\jjwt-api-0.11.5.jar",
    "$MAVEN_REPO\io\jsonwebtoken\jjwt-impl\0.11.5\jjwt-impl-0.11.5.jar",
    "$MAVEN_REPO\io\jsonwebtoken\jjwt-jackson\0.11.5\jjwt-jackson-0.11.5.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\core\jackson-databind\2.15.4\jackson-databind-2.15.4.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\core\jackson-annotations\2.15.4\jackson-annotations-2.15.4.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\core\jackson-core\2.15.4\jackson-core-2.15.4.jar",
    "$MAVEN_REPO\com\vaadin\external\google\android-json\0.0.20131108.vaadin1\android-json-0.0.20131108.vaadin1.jar",
    "$MAVEN_REPO\org\apache\commons\commons-lang3\3.14.0\commons-lang3-3.14.0.jar",
    "$MAVEN_REPO\org\projectlombok\lombok\1.18.30\lombok-1.18.30.jar",
    "$MAVEN_REPO\jakarta\xml\bind\jakarta.xml.bind-api\4.0.1\jakarta.xml.bind-api-4.0.1.jar",
    "$MAVEN_REPO\jakarta\activation\jakarta.activation-api\2.1.2\jakarta.activation-api-2.1.2.jar",
    "$MAVEN_REPO\org\springframework\spring-core\6.1.4\spring-core-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-jcl\6.1.4\spring-jcl-6.1.4.jar",
    "$MAVEN_REPO\org\springdoc\springdoc-openapi-starter-webmvc-ui\2.5.0\springdoc-openapi-starter-webmvc-ui-2.5.0.jar",
    "$MAVEN_REPO\org\springdoc\springdoc-openapi-starter-webmvc-api\2.5.0\springdoc-openapi-starter-webmvc-api-2.5.0.jar",
    "$MAVEN_REPO\org\springdoc\springdoc-openapi-starter-common\2.5.0\springdoc-openapi-starter-common-2.5.0.jar",
    "$MAVEN_REPO\io\swagger\core\v3\swagger-core-jakarta\2.2.21\swagger-core-jakarta-2.2.21.jar",
    "$MAVEN_REPO\io\swagger\core\v3\swagger-annotations-jakarta\2.2.21\swagger-annotations-jakarta-2.2.21.jar",
    "$MAVEN_REPO\io\swagger\core\v3\swagger-models-jakarta\2.2.21\swagger-models-jakarta-2.2.21.jar",
    "$MAVEN_REPO\jakarta\validation\jakarta.validation-api\3.0.2\jakarta.validation-api-3.0.2.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\dataformat\jackson-dataformat-yaml\2.15.4\jackson-dataformat-yaml-2.15.4.jar",
    "$MAVEN_REPO\org\webjars\swagger-ui\5.13.0\swagger-ui-5.13.0.jar",
    "$MAVEN_REPO\net\bytebuddy\byte-buddy\1.14.12\byte-buddy-1.14.12.jar",
    "$MAVEN_REPO\org\slf4j\slf4j-api\2.0.9\slf4j-api-2.0.9.jar",
    "$MAVEN_REPO\ch\qos\logback\logback-classic\1.4.14\logback-classic-1.4.14.jar",
    "$MAVEN_REPO\ch\qos\logback\logback-core\1.4.14\logback-core-1.4.14.jar"
) -join ";"

# Step 4: Start Leave Service with JaCoCo (tcpserver mode for live dump)
Write-Host "Step 4: Starting Leave Service (conge) with JaCoCo tcpserver on port 9000..."
$CONGE_JACOCO_OPTS = '-javaagent:{0}=output=tcpserver,port=36320,address=127.0.0.1,dumponexit=true,destfile={1}\conge.exec' -f $JACOCO_AGENT,$OUTPUT_DIR
$CONGE_CMD = @(
    "`"$JAVA_EXE`"",
    "$CONGE_JACOCO_OPTS",
    "-Dfile.encoding=UTF-8",
    "-cp `"$CONGE_CLASSPATH`"",
    "-Dserver.port=9000",
    "tn.enis.conge.CongeeApplication"
) -join " "

Write-Host "  Command: $CONGE_CMD"
Write-Host "  (Starting in background...)"
$CONGE_PROCESS = Start-Process -FilePath "$JAVA_EXE" -ArgumentList @(
    $CONGE_JACOCO_OPTS,
    "-Dfile.encoding=UTF-8",
    "-cp", $CONGE_CLASSPATH,
    "-Dserver.port=9000",
    "tn.enis.conge.CongeeApplication"
) -NoNewWindow -PassThru
Write-Host "  Leave Service started (PID: $($CONGE_PROCESS.Id))"

# Wait for service to start
Start-Sleep -Seconds 5

# Step 5: Verify Leave Service is running
Write-Host "Step 5: Verifying Leave Service..."
$response = $null
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9000/api/health" -Method GET -ErrorAction SilentlyContinue
    Write-Host "  ✓ Leave Service is responding on port 9000"
} catch {
    Write-Host "  ⚠ Leave Service may still be starting... (HTTP response: $($_.Exception.Response.StatusCode))"
}

# Step 6: Start Auth Service with JaCoCo
Write-Host "Step 6: Starting Auth Service (DemandeConge) with JaCoCo on port 9001..."
$AUTH_CLASSPATH = @(
    "$DEMANDE_CONGE_PATH",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-actuator\3.2.3\spring-boot-starter-actuator-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter\3.2.3\spring-boot-starter-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot\3.2.3\spring-boot-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-autoconfigure\3.2.3\spring-boot-autoconfigure-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-logging\3.2.3\spring-boot-starter-logging-3.2.3.jar",
    "$MAVEN_REPO\org\apache\logging\log4j\log4j-to-slf4j\2.21.1\log4j-to-slf4j-2.21.1.jar",
    "$MAVEN_REPO\org\apache\logging\log4j\log4j-api\2.21.1\log4j-api-2.21.1.jar",
    "$MAVEN_REPO\org\slf4j\jul-to-slf4j\2.0.12\jul-to-slf4j-2.0.12.jar",
    "$MAVEN_REPO\jakarta\annotation\jakarta.annotation-api\2.1.1\jakarta.annotation-api-2.1.1.jar",
    "$MAVEN_REPO\org\yaml\snakeyaml\2.2\snakeyaml-2.2.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-actuator-autoconfigure\3.2.3\spring-boot-actuator-autoconfigure-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-actuator\3.2.3\spring-boot-actuator-3.2.3.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\datatype\jackson-datatype-jsr310\2.15.4\jackson-datatype-jsr310-2.15.4.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-observation\1.12.3\micrometer-observation-1.12.3.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-commons\1.12.3\micrometer-commons-1.12.3.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-jakarta9\1.12.3\micrometer-jakarta9-1.12.3.jar",
    "$MAVEN_REPO\io\micrometer\micrometer-core\1.12.3\micrometer-core-1.12.3.jar",
    "$MAVEN_REPO\org\hdrhistogram\HdrHistogram\2.1.12\HdrHistogram-2.1.12.jar",
    "$MAVEN_REPO\org\latencyutils\LatencyUtils\2.0.3\LatencyUtils-2.0.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-web\3.2.3\spring-boot-starter-web-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-json\3.2.3\spring-boot-starter-json-3.2.3.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\datatype\jackson-datatype-jdk8\2.15.4\jackson-datatype-jdk8-2.15.4.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\module\jackson-module-parameter-names\2.15.4\jackson-module-parameter-names-2.15.4.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-tomcat\3.2.3\spring-boot-starter-tomcat-3.2.3.jar",
    "$MAVEN_REPO\org\apache\tomcat\embed\tomcat-embed-core\10.1.19\tomcat-embed-core-10.1.19.jar",
    "$MAVEN_REPO\org\apache\tomcat\embed\tomcat-embed-el\10.1.19\tomcat-embed-el-10.1.19.jar",
    "$MAVEN_REPO\org\apache\tomcat\embed\tomcat-embed-websocket\10.1.19\tomcat-embed-websocket-10.1.19.jar",
    "$MAVEN_REPO\org\springframework\spring-web\6.1.4\spring-web-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-beans\6.1.4\spring-beans-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-webmvc\6.1.4\spring-webmvc-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-context\6.1.4\spring-context-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-expression\6.1.4\spring-expression-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-data-jpa\3.2.3\spring-boot-starter-data-jpa-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-aop\3.2.3\spring-boot-starter-aop-3.2.3.jar",
    "$MAVEN_REPO\org\aspectj\aspectjweaver\1.9.21\aspectjweaver-1.9.21.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-jdbc\3.2.3\spring-boot-starter-jdbc-3.2.3.jar",
    "$MAVEN_REPO\com\zaxxer\HikariCP\5.0.1\HikariCP-5.0.1.jar",
    "$MAVEN_REPO\org\springframework\spring-jdbc\6.1.4\spring-jdbc-6.1.4.jar",
    "$MAVEN_REPO\org\hibernate\orm\hibernate-core\6.4.4.Final\hibernate-core-6.4.4.Final.jar",
    "$MAVEN_REPO\jakarta\persistence\jakarta.persistence-api\3.1.0\jakarta.persistence-api-3.1.0.jar",
    "$MAVEN_REPO\jakarta\transaction\jakarta.transaction-api\2.0.1\jakarta.transaction-api-2.0.1.jar",
    "$MAVEN_REPO\org\jboss\logging\jboss-logging\3.5.3.Final\jboss-logging-3.5.3.Final.jar",
    "$MAVEN_REPO\org\hibernate\common\hibernate-commons-annotations\6.0.6.Final\hibernate-commons-annotations-6.0.6.Final.jar",
    "$MAVEN_REPO\io\smallrye\jandex\3.1.2\jandex-3.1.2.jar",
    "$MAVEN_REPO\com\fasterxml\classmate\1.6.0\classmate-1.6.0.jar",
    "$MAVEN_REPO\org\glassfish\jaxb\jaxb-runtime\4.0.4\jaxb-runtime-4.0.4.jar",
    "$MAVEN_REPO\com\mysql\mysql-connector-j\8.0.33\mysql-connector-j-8.0.33.jar",
    "$MAVEN_REPO\org\projectlombok\lombok\1.18.30\lombok-1.18.30.jar",
    "$MAVEN_REPO\org\springframework\cloud\spring-cloud-starter-openfeign\4.1.4\spring-cloud-starter-openfeign-4.1.4.jar",
    "$MAVEN_REPO\org\springframework\cloud\spring-cloud-starter\4.1.5\spring-cloud-starter-4.1.5.jar",
    "$MAVEN_REPO\org\springframework\cloud\spring-cloud-context\4.1.5\spring-cloud-context-4.1.5.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-rsa\1.1.3\spring-security-rsa-1.1.3.jar",
    "$MAVEN_REPO\org\bouncycastle\bcprov-jdk18on\1.78\bcprov-jdk18on-1.78.jar",
    "$MAVEN_REPO\org\springframework\cloud\spring-cloud-openfeign-core\4.1.4\spring-cloud-openfeign-core-4.1.4.jar",
    "$MAVEN_REPO\io\github\openfeign\feign-form-spring\13.5\feign-form-spring-13.5.jar",
    "$MAVEN_REPO\io\github\openfeign\feign-form\13.5\feign-form-13.5.jar",
    "$MAVEN_REPO\commons-fileupload\commons-fileupload\1.5\commons-fileupload-1.5.jar",
    "$MAVEN_REPO\commons-io\commons-io\2.11.0\commons-io-2.11.0.jar",
    "$MAVEN_REPO\org\springframework\cloud\spring-cloud-commons\4.1.5\spring-cloud-commons-4.1.5.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-crypto\6.2.2\spring-security-crypto-6.2.2.jar",
    "$MAVEN_REPO\io\github\openfeign\feign-core\13.5\feign-core-13.5.jar",
    "$MAVEN_REPO\io\github\openfeign\feign-slf4j\13.5\feign-slf4j-13.5.jar",
    "$MAVEN_REPO\org\springframework\boot\spring-boot-starter-security\3.2.3\spring-boot-starter-security-3.2.3.jar",
    "$MAVEN_REPO\org\springframework\spring-aop\6.1.4\spring-aop-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-config\6.2.2\spring-security-config-6.2.2.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-core\6.2.2\spring-security-core-6.2.2.jar",
    "$MAVEN_REPO\org\springframework\security\spring-security-web\6.2.2\spring-security-web-6.2.2.jar",
    "$MAVEN_REPO\io\jsonwebtoken\jjwt-api\0.11.5\jjwt-api-0.11.5.jar",
    "$MAVEN_REPO\io\jsonwebtoken\jjwt-impl\0.11.5\jjwt-impl-0.11.5.jar",
    "$MAVEN_REPO\io\jsonwebtoken\jjwt-jackson\0.11.5\jjwt-jackson-0.11.5.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\core\jackson-databind\2.15.4\jackson-databind-2.15.4.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\core\jackson-annotations\2.15.4\jackson-annotations-2.15.4.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\core\jackson-core\2.15.4\jackson-core-2.15.4.jar",
    "$MAVEN_REPO\jakarta\xml\bind\jakarta.xml.bind-api\4.0.1\jakarta.xml.bind-api-4.0.1.jar",
    "$MAVEN_REPO\jakarta\activation\jakarta.activation-api\2.1.2\jakarta.activation-api-2.1.2.jar",
    "$MAVEN_REPO\org\springframework\spring-core\6.1.4\spring-core-6.1.4.jar",
    "$MAVEN_REPO\org\springframework\spring-jcl\6.1.4\spring-jcl-6.1.4.jar",
    "$MAVEN_REPO\org\springdoc\springdoc-openapi-starter-webmvc-ui\2.5.0\springdoc-openapi-starter-webmvc-ui-2.5.0.jar",
    "$MAVEN_REPO\org\springdoc\springdoc-openapi-starter-webmvc-api\2.5.0\springdoc-openapi-starter-webmvc-api-2.5.0.jar",
    "$MAVEN_REPO\org\springdoc\springdoc-openapi-starter-common\2.5.0\springdoc-openapi-starter-common-2.5.0.jar",
    "$MAVEN_REPO\io\swagger\core\v3\swagger-core-jakarta\2.2.21\swagger-core-jakarta-2.2.21.jar",
    "$MAVEN_REPO\io\swagger\core\v3\swagger-annotations-jakarta\2.2.21\swagger-annotations-jakarta-2.2.21.jar",
    "$MAVEN_REPO\io\swagger\core\v3\swagger-models-jakarta\2.2.21\swagger-models-jakarta-2.2.21.jar",
    "$MAVEN_REPO\jakarta\validation\jakarta.validation-api\3.0.2\jakarta.validation-api-3.0.2.jar",
    "$MAVEN_REPO\com\fasterxml\jackson\dataformat\jackson-dataformat-yaml\2.15.4\jackson-dataformat-yaml-2.15.4.jar",
    "$MAVEN_REPO\org\webjars\swagger-ui\5.13.0\swagger-ui-5.13.0.jar",
    "$MAVEN_REPO\net\bytebuddy\byte-buddy\1.14.12\byte-buddy-1.14.12.jar",
    "$MAVEN_REPO\org\slf4j\slf4j-api\2.0.9\slf4j-api-2.0.9.jar",
    "$MAVEN_REPO\ch\qos\logback\logback-classic\1.4.14\logback-classic-1.4.14.jar",
    "$MAVEN_REPO\ch\qos\logback\logback-core\1.4.14\logback-core-1.4.14.jar",
    "$MAVEN_REPO\com\vaadin\external\google\android-json\0.0.20131108.vaadin1\android-json-0.0.20131108.vaadin1.jar",
    "$MAVEN_REPO\org\apache\commons\commons-lang3\3.13.0\commons-lang3-3.13.0.jar"
) -join ";"

$AUTH_JACOCO_OPTS = '-javaagent:{0}=output=tcpserver,port=36321,address=127.0.0.1,dumponexit=true,destfile={1}\auth.exec' -f $JACOCO_AGENT,$OUTPUT_DIR
Write-Host "  Command arguments prepared"
Write-Host "  (Starting in background...)"
$AUTH_PROCESS = Start-Process -FilePath "$JAVA_EXE" -ArgumentList @(
    $AUTH_JACOCO_OPTS,
    "-Dfile.encoding=UTF-8",
    "-cp", $AUTH_CLASSPATH,
    "-Dserver.port=9001",
    "tn.enis.DemandeConge.DemandeCongeApplication"
) -NoNewWindow -PassThru
Write-Host "  Auth Service started (PID: $($AUTH_PROCESS.Id))"

# Wait for service to start
Start-Sleep -Seconds 5

# Step 7: Verify Auth Service is running
Write-Host "Step 7: Verifying Auth Service..."
$response = $null
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9001/api/health" -Method GET -ErrorAction SilentlyContinue
    Write-Host "  ✓ Auth Service is responding on port 9001"
} catch {
    Write-Host "  ⚠ Auth Service may still be starting..."
}

# Step 8: Summary
Write-Host ""
Write-Host "=========================================="
Write-Host "Services Restart Complete!"
Write-Host "=========================================="
Write-Host "Leave Service (conge):"
Write-Host "  - Port: 9000"
Write-Host "  - PID: $($CONGE_PROCESS.Id)"
Write-Host "  - JaCoCo Output: $OUTPUT_DIR\conge.exec"
Write-Host ""
Write-Host "Auth Service (DemandeConge):"
Write-Host "  - Port: 9001"
Write-Host "  - PID: $($AUTH_PROCESS.Id)"
Write-Host "  - JaCoCo Output: $OUTPUT_DIR\auth.exec"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run tests to collect coverage data:"
Write-Host "     python run_pipeline.py --services auth"
Write-Host "  2. Fresh coverage data will be saved to:"
Write-Host "     $OUTPUT_DIR\"
Write-Host "=========================================="
