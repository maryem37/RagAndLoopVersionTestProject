# Script to restart Java microservices with JaCoCo agent monitoring
# This enables coverage data collection for the microservices

param(
    [switch]$SkipKill = $false
)

# Configuration
$JAVA_EXE = "C:\Program Files\Java\jdk-17\bin\java.exe"
$JACOCO_AGENT = "$env:USERPROFILE\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar"
$OUTPUT_DIR = "C:\Bureau\Bureau\project_test\output\jacoco"

# Create output directory if it doesn't exist
if (-not (Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Path $OUTPUT_DIR -Force | Out-Null
    Write-Host "✓ Created output directory: $OUTPUT_DIR"
}

# Verify prerequisites
if (-not (Test-Path $JAVA_EXE)) {
    Write-Host "❌ Java not found at: $JAVA_EXE"
    exit 1
}

if (-not (Test-Path $JACOCO_AGENT)) {
    Write-Host "❌ JaCoCo agent not found at: $JACOCO_AGENT"
    exit 1
}

Write-Host "✓ JaCoCo agent found: $JACOCO_AGENT"

# Step 1: Stop existing services
if (-not $SkipKill) {
    Write-Host "`n[Step 1] Stopping existing Java services..."
    $killed = $false
    
    # Try killing by port
    try {
        $netstat = netstat -ano 2>$null | Select-String ":9000|:9001"
        foreach ($line in $netstat) {
            $parts = $line -split '\s+' | Where-Object {$_}
            if ($parts.Count -ge 5) {
                $pid = $parts[-1]
                $port = if ($line -match ':9000') { '9000' } else { '9001' }
                Write-Host "  Killing PID $pid on port $port..."
                taskkill /PID $pid /F 2>$null | Out-Null
                $killed = $true
            }
        }
    } catch {}
    
    # If that didn't work, kill all java.exe
    if (-not $killed) {
        Write-Host "  Killing all java.exe processes..."
        taskkill /IM java.exe /F 2>$null | Out-Null
    }
    
    Start-Sleep -Seconds 3
    Write-Host "  ✓ Services stopped"
}

# Step 2: Prepare classpath for Conge Service
# This is the classpath extracted from the running process earlier
$CONGE_CLASSPATH = @(
    "C:\Bureau\Bureau\microservices\conge\target\classes",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-actuator\3.2.3\spring-boot-starter-actuator-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter\3.2.3\spring-boot-starter-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot\3.2.3\spring-boot-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-autoconfigure\3.2.3\spring-boot-autoconfigure-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-logging\3.2.3\spring-boot-starter-logging-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\logging\log4j\log4j-to-slf4j\2.21.1\log4j-to-slf4j-2.21.1.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\logging\log4j\log4j-api\2.21.1\log4j-api-2.21.1.jar",
    "$env:USERPROFILE\.m2\repository\org\slf4j\jul-to-slf4j\2.0.12\jul-to-slf4j-2.0.12.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\annotation\jakarta.annotation-api\2.1.1\jakarta.annotation-api-2.1.1.jar",
    "$env:USERPROFILE\.m2\repository\org\yaml\snakeyaml\2.2\snakeyaml-2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-actuator-autoconfigure\3.2.3\spring-boot-actuator-autoconfigure-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-actuator\3.2.3\spring-boot-actuator-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\datatype\jackson-datatype-jsr310\2.15.4\jackson-datatype-jsr310-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-observation\1.12.3\micrometer-observation-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-commons\1.12.3\micrometer-commons-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-jakarta9\1.12.3\micrometer-jakarta9-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-core\1.12.3\micrometer-core-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\org\hdrhistogram\HdrHistogram\2.1.12\HdrHistogram-2.1.12.jar",
    "$env:USERPROFILE\.m2\repository\org\latencyutils\LatencyUtils\2.0.3\LatencyUtils-2.0.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-data-jpa\3.2.3\spring-boot-starter-data-jpa-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-aop\3.2.3\spring-boot-starter-aop-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\aspectj\aspectjweaver\1.9.21\aspectjweaver-1.9.21.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-jdbc\3.2.3\spring-boot-starter-jdbc-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\com\zaxxer\HikariCP\5.0.1\HikariCP-5.0.1.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-jdbc\6.1.4\spring-jdbc-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\hibernate\orm\hibernate-core\6.4.4.Final\hibernate-core-6.4.4.Final.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\persistence\jakarta.persistence-api\3.1.0\jakarta.persistence-api-3.1.0.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\transaction\jakarta.transaction-api\2.0.1\jakarta.transaction-api-2.0.1.jar",
    "$env:USERPROFILE\.m2\repository\org\jboss\logging\jboss-logging\3.5.3.Final\jboss-logging-3.5.3.Final.jar",
    "$env:USERPROFILE\.m2\repository\org\hibernate\common\hibernate-commons-annotations\6.0.6.Final\hibernate-commons-annotations-6.0.6.Final.jar",
    "$env:USERPROFILE\.m2\repository\io\smallrye\jandex\3.1.2\jandex-3.1.2.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\classmate\1.6.0\classmate-1.6.0.jar",
    "$env:USERPROFILE\.m2\repository\org\glassfish\jaxb\jaxb-runtime\4.0.4\jaxb-runtime-4.0.4.jar",
    "$env:USERPROFILE\.m2\repository\org\glassfish\jaxb\jaxb-core\4.0.4\jaxb-core-4.0.4.jar",
    "$env:USERPROFILE\.m2\repository\org\eclipse\angus\angus-activation\2.0.1\angus-activation-2.0.1.jar",
    "$env:USERPROFILE\.m2\repository\org\glassfish\jaxb\txw2\4.0.4\txw2-4.0.4.jar",
    "$env:USERPROFILE\.m2\repository\com\sun\istack\istack-commons-runtime\4.1.2\istack-commons-runtime-4.1.2.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\inject\jakarta.inject-api\2.0.1\jakarta.inject-api-2.0.1.jar",
    "$env:USERPROFILE\.m2\repository\org\antlr\antlr4-runtime\4.13.0\antlr4-runtime-4.13.0.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\data\spring-data-jpa\3.2.3\spring-data-jpa-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\data\spring-data-commons\3.2.3\spring-data-commons-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-orm\6.1.4\spring-orm-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-context\6.1.4\spring-context-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-tx\6.1.4\spring-tx-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-beans\6.1.4\spring-beans-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-aspects\6.1.4\spring-aspects-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-web\3.2.3\spring-boot-starter-web-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-json\3.2.3\spring-boot-starter-json-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\datatype\jackson-datatype-jdk8\2.15.4\jackson-datatype-jdk8-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\module\jackson-module-parameter-names\2.15.4\jackson-module-parameter-names-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-tomcat\3.2.3\spring-boot-starter-tomcat-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\tomcat\embed\tomcat-embed-core\10.1.19\tomcat-embed-core-10.1.19.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\tomcat\embed\tomcat-embed-el\10.1.19\tomcat-embed-el-10.1.19.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\tomcat\embed\tomcat-embed-websocket\10.1.19\tomcat-embed-websocket-10.1.19.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-web\6.1.4\spring-web-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-webmvc\6.1.4\spring-webmvc-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-expression\6.1.4\spring-expression-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\com\mysql\mysql-connector-j\8.0.33\mysql-connector-j-8.0.33.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-security\3.2.3\spring-boot-starter-security-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-aop\6.1.4\spring-aop-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-config\6.2.2\spring-security-config-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-core\6.2.2\spring-security-core-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-crypto\6.2.2\spring-security-crypto-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-web\6.2.2\spring-security-web-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\io\jsonwebtoken\jjwt-api\0.11.5\jjwt-api-0.11.5.jar",
    "$env:USERPROFILE\.m2\repository\io\jsonwebtoken\jjwt-impl\0.11.5\jjwt-impl-0.11.5.jar",
    "$env:USERPROFILE\.m2\repository\io\jsonwebtoken\jjwt-jackson\0.11.5\jjwt-jackson-0.11.5.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\core\jackson-databind\2.15.4\jackson-databind-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\core\jackson-annotations\2.15.4\jackson-annotations-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\core\jackson-core\2.15.4\jackson-core-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\vaadin\external\google\android-json\0.0.20131108.vaadin1\android-json-0.0.20131108.vaadin1.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\commons\commons-lang3\3.14.0\commons-lang3-3.14.0.jar",
    "$env:USERPROFILE\.m2\repository\org\projectlombok\lombok\1.18.30\lombok-1.18.30.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\xml\bind\jakarta.xml.bind-api\4.0.1\jakarta.xml.bind-api-4.0.1.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\activation\jakarta.activation-api\2.1.2\jakarta.activation-api-2.1.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-core\6.1.4\spring-core-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-jcl\6.1.4\spring-jcl-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springdoc\springdoc-openapi-starter-webmvc-ui\2.5.0\springdoc-openapi-starter-webmvc-ui-2.5.0.jar",
    "$env:USERPROFILE\.m2\repository\org\springdoc\springdoc-openapi-starter-webmvc-api\2.5.0\springdoc-openapi-starter-webmvc-api-2.5.0.jar",
    "$env:USERPROFILE\.m2\repository\org\springdoc\springdoc-openapi-starter-common\2.5.0\springdoc-openapi-starter-common-2.5.0.jar",
    "$env:USERPROFILE\.m2\repository\io\swagger\core\v3\swagger-core-jakarta\2.2.21\swagger-core-jakarta-2.2.21.jar",
    "$env:USERPROFILE\.m2\repository\io\swagger\core\v3\swagger-annotations-jakarta\2.2.21\swagger-annotations-jakarta-2.2.21.jar",
    "$env:USERPROFILE\.m2\repository\io\swagger\core\v3\swagger-models-jakarta\2.2.21\swagger-models-jakarta-2.2.21.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\validation\jakarta.validation-api\3.0.2\jakarta.validation-api-3.0.2.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\dataformat\jackson-dataformat-yaml\2.15.4\jackson-dataformat-yaml-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\org\webjars\swagger-ui\5.13.0\swagger-ui-5.13.0.jar",
    "$env:USERPROFILE\.m2\repository\net\bytebuddy\byte-buddy\1.14.12\byte-buddy-1.14.12.jar",
    "$env:USERPROFILE\.m2\repository\org\slf4j\slf4j-api\2.0.9\slf4j-api-2.0.9.jar",
    "$env:USERPROFILE\.m2\repository\ch\qos\logback\logback-classic\1.4.14\logback-classic-1.4.14.jar",
    "$env:USERPROFILE\.m2\repository\ch\qos\logback\logback-core\1.4.14\logback-core-1.4.14.jar"
) -join ";"

# Step 3: Start Conge Service with JaCoCo
Write-Host "`n[Step 2] Starting Leave Service (conge) on port 9000 with JaCoCo..."
$CONGE_JACOCO_OPTS = "-javaagent:${JACOCO_AGENT}=destfile=$OUTPUT_DIR\conge.exec,append=false"
Write-Host "  JaCoCo output: $OUTPUT_DIR\conge.exec"

$CONGE_PROCESS = Start-Process -FilePath $JAVA_EXE -ArgumentList @(
    $CONGE_JACOCO_OPTS,
    "-Dfile.encoding=UTF-8",
    "-cp", $CONGE_CLASSPATH,
    "-Dserver.port=9000",
    "tn.enis.conge.CongeeApplication"
) -NoNewWindow -PassThru

Write-Host "  ✓ Leave Service started (PID: $($CONGE_PROCESS.Id))"
Start-Sleep -Seconds 5

# Step 4: Verify Leave Service
Write-Host "`n[Step 3] Verifying Leave Service..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9000/api/health" -ErrorAction Stop -TimeoutSec 2
    Write-Host "  ✓ Leave Service is responding on port 9000"
} catch {
    Write-Host "  ⚠ Leave Service may still be starting (response: $($_.Exception.Response.StatusCode))"
}

# Step 5: Prepare classpath for DemandeConge Service (Auth)
Write-Host "`n[Step 4] Starting Auth Service (DemandeConge) on port 9001 with JaCoCo..."
$AUTH_CLASSPATH = @(
    "C:\Bureau\Bureau\microservices\DemandeConge\target\classes",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-actuator\3.2.3\spring-boot-starter-actuator-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter\3.2.3\spring-boot-starter-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot\3.2.3\spring-boot-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-autoconfigure\3.2.3\spring-boot-autoconfigure-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-logging\3.2.3\spring-boot-starter-logging-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\logging\log4j\log4j-to-slf4j\2.21.1\log4j-to-slf4j-2.21.1.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\logging\log4j\log4j-api\2.21.1\log4j-api-2.21.1.jar",
    "$env:USERPROFILE\.m2\repository\org\slf4j\jul-to-slf4j\2.0.12\jul-to-slf4j-2.0.12.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\annotation\jakarta.annotation-api\2.1.1\jakarta.annotation-api-2.1.1.jar",
    "$env:USERPROFILE\.m2\repository\org\yaml\snakeyaml\2.2\snakeyaml-2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-actuator-autoconfigure\3.2.3\spring-boot-actuator-autoconfigure-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-actuator\3.2.3\spring-boot-actuator-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\datatype\jackson-datatype-jsr310\2.15.4\jackson-datatype-jsr310-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-observation\1.12.3\micrometer-observation-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-commons\1.12.3\micrometer-commons-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-jakarta9\1.12.3\micrometer-jakarta9-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\io\micrometer\micrometer-core\1.12.3\micrometer-core-1.12.3.jar",
    "$env:USERPROFILE\.m2\repository\org\hdrhistogram\HdrHistogram\2.1.12\HdrHistogram-2.1.12.jar",
    "$env:USERPROFILE\.m2\repository\org\latencyutils\LatencyUtils\2.0.3\LatencyUtils-2.0.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-web\3.2.3\spring-boot-starter-web-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-json\3.2.3\spring-boot-starter-json-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\datatype\jackson-datatype-jdk8\2.15.4\jackson-datatype-jdk8-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\module\jackson-module-parameter-names\2.15.4\jackson-module-parameter-names-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-tomcat\3.2.3\spring-boot-starter-tomcat-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\tomcat\embed\tomcat-embed-core\10.1.19\tomcat-embed-core-10.1.19.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\tomcat\embed\tomcat-embed-el\10.1.19\tomcat-embed-el-10.1.19.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\tomcat\embed\tomcat-embed-websocket\10.1.19\tomcat-embed-websocket-10.1.19.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-web\6.1.4\spring-web-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-beans\6.1.4\spring-beans-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-webmvc\6.1.4\spring-webmvc-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-context\6.1.4\spring-context-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-expression\6.1.4\spring-expression-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-data-jpa\3.2.3\spring-boot-starter-data-jpa-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-aop\3.2.3\spring-boot-starter-aop-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\aspectj\aspectjweaver\1.9.21\aspectjweaver-1.9.21.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-jdbc\3.2.3\spring-boot-starter-jdbc-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\com\zaxxer\HikariCP\5.0.1\HikariCP-5.0.1.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-jdbc\6.1.4\spring-jdbc-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\hibernate\orm\hibernate-core\6.4.4.Final\hibernate-core-6.4.4.Final.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\persistence\jakarta.persistence-api\3.1.0\jakarta.persistence-api-3.1.0.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\transaction\jakarta.transaction-api\2.0.1\jakarta.transaction-api-2.0.1.jar",
    "$env:USERPROFILE\.m2\repository\org\jboss\logging\jboss-logging\3.5.3.Final\jboss-logging-3.5.3.Final.jar",
    "$env:USERPROFILE\.m2\repository\org\hibernate\common\hibernate-commons-annotations\6.0.6.Final\hibernate-commons-annotations-6.0.6.Final.jar",
    "$env:USERPROFILE\.m2\repository\io\smallrye\jandex\3.1.2\jandex-3.1.2.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\classmate\1.6.0\classmate-1.6.0.jar",
    "$env:USERPROFILE\.m2\repository\org\glassfish\jaxb\jaxb-runtime\4.0.4\jaxb-runtime-4.0.4.jar",
    "$env:USERPROFILE\.m2\repository\com\mysql\mysql-connector-j\8.0.33\mysql-connector-j-8.0.33.jar",
    "$env:USERPROFILE\.m2\repository\org\projectlombok\lombok\1.18.30\lombok-1.18.30.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\cloud\spring-cloud-starter-openfeign\4.1.4\spring-cloud-starter-openfeign-4.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\cloud\spring-cloud-starter\4.1.5\spring-cloud-starter-4.1.5.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\cloud\spring-cloud-context\4.1.5\spring-cloud-context-4.1.5.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-rsa\1.1.3\spring-security-rsa-1.1.3.jar",
    "$env:USERPROFILE\.m2\repository\org\bouncycastle\bcprov-jdk18on\1.78\bcprov-jdk18on-1.78.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\cloud\spring-cloud-openfeign-core\4.1.4\spring-cloud-openfeign-core-4.1.4.jar",
    "$env:USERPROFILE\.m2\repository\io\github\openfeign\feign-form-spring\13.5\feign-form-spring-13.5.jar",
    "$env:USERPROFILE\.m2\repository\io\github\openfeign\feign-form\13.5\feign-form-13.5.jar",
    "$env:USERPROFILE\.m2\repository\commons-fileupload\commons-fileupload\1.5\commons-fileupload-1.5.jar",
    "$env:USERPROFILE\.m2\repository\commons-io\commons-io\2.11.0\commons-io-2.11.0.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\cloud\spring-cloud-commons\4.1.5\spring-cloud-commons-4.1.5.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-crypto\6.2.2\spring-security-crypto-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\io\github\openfeign\feign-core\13.5\feign-core-13.5.jar",
    "$env:USERPROFILE\.m2\repository\io\github\openfeign\feign-slf4j\13.5\feign-slf4j-13.5.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\boot\spring-boot-starter-security\3.2.3\spring-boot-starter-security-3.2.3.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-aop\6.1.4\spring-aop-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-config\6.2.2\spring-security-config-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-core\6.2.2\spring-security-core-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\security\spring-security-web\6.2.2\spring-security-web-6.2.2.jar",
    "$env:USERPROFILE\.m2\repository\io\jsonwebtoken\jjwt-api\0.11.5\jjwt-api-0.11.5.jar",
    "$env:USERPROFILE\.m2\repository\io\jsonwebtoken\jjwt-impl\0.11.5\jjwt-impl-0.11.5.jar",
    "$env:USERPROFILE\.m2\repository\io\jsonwebtoken\jjwt-jackson\0.11.5\jjwt-jackson-0.11.5.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\core\jackson-databind\2.15.4\jackson-databind-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\core\jackson-annotations\2.15.4\jackson-annotations-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\core\jackson-core\2.15.4\jackson-core-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\xml\bind\jakarta.xml.bind-api\4.0.1\jakarta.xml.bind-api-4.0.1.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\activation\jakarta.activation-api\2.1.2\jakarta.activation-api-2.1.2.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-core\6.1.4\spring-core-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springframework\spring-jcl\6.1.4\spring-jcl-6.1.4.jar",
    "$env:USERPROFILE\.m2\repository\org\springdoc\springdoc-openapi-starter-webmvc-ui\2.5.0\springdoc-openapi-starter-webmvc-ui-2.5.0.jar",
    "$env:USERPROFILE\.m2\repository\org\springdoc\springdoc-openapi-starter-webmvc-api\2.5.0\springdoc-openapi-starter-webmvc-api-2.5.0.jar",
    "$env:USERPROFILE\.m2\repository\org\springdoc\springdoc-openapi-starter-common\2.5.0\springdoc-openapi-starter-common-2.5.0.jar",
    "$env:USERPROFILE\.m2\repository\io\swagger\core\v3\swagger-core-jakarta\2.2.21\swagger-core-jakarta-2.2.21.jar",
    "$env:USERPROFILE\.m2\repository\io\swagger\core\v3\swagger-annotations-jakarta\2.2.21\swagger-annotations-jakarta-2.2.21.jar",
    "$env:USERPROFILE\.m2\repository\io\swagger\core\v3\swagger-models-jakarta\2.2.21\swagger-models-jakarta-2.2.21.jar",
    "$env:USERPROFILE\.m2\repository\jakarta\validation\jakarta.validation-api\3.0.2\jakarta.validation-api-3.0.2.jar",
    "$env:USERPROFILE\.m2\repository\com\fasterxml\jackson\dataformat\jackson-dataformat-yaml\2.15.4\jackson-dataformat-yaml-2.15.4.jar",
    "$env:USERPROFILE\.m2\repository\org\webjars\swagger-ui\5.13.0\swagger-ui-5.13.0.jar",
    "$env:USERPROFILE\.m2\repository\net\bytebuddy\byte-buddy\1.14.12\byte-buddy-1.14.12.jar",
    "$env:USERPROFILE\.m2\repository\org\slf4j\slf4j-api\2.0.9\slf4j-api-2.0.9.jar",
    "$env:USERPROFILE\.m2\repository\ch\qos\logback\logback-classic\1.4.14\logback-classic-1.4.14.jar",
    "$env:USERPROFILE\.m2\repository\ch\qos\logback\logback-core\1.4.14\logback-core-1.4.14.jar",
    "$env:USERPROFILE\.m2\repository\com\vaadin\external\google\android-json\0.0.20131108.vaadin1\android-json-0.0.20131108.vaadin1.jar",
    "$env:USERPROFILE\.m2\repository\org\apache\commons\commons-lang3\3.13.0\commons-lang3-3.13.0.jar"
) -join ";"

$AUTH_JACOCO_OPTS = "-javaagent:${JACOCO_AGENT}=destfile=$OUTPUT_DIR\auth.exec,append=false"
Write-Host "  JaCoCo output: $OUTPUT_DIR\auth.exec"

$AUTH_PROCESS = Start-Process -FilePath $JAVA_EXE -ArgumentList @(
    $AUTH_JACOCO_OPTS,
    "-Dfile.encoding=UTF-8",
    "-cp", $AUTH_CLASSPATH,
    "-Dserver.port=9001",
    "tn.enis.DemandeConge.DemandeCongeApplication"
) -NoNewWindow -PassThru

Write-Host "  ✓ Auth Service started (PID: $($AUTH_PROCESS.Id))"
Start-Sleep -Seconds 5

# Step 6: Verify Auth Service
Write-Host "`n[Step 5] Verifying Auth Service..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9001/api/health" -ErrorAction Stop -TimeoutSec 2
    Write-Host "  ✓ Auth Service is responding on port 9001"
} catch {
    Write-Host "  ⚠ Auth Service may still be starting (response: $($_.Exception.Response.StatusCode))"
}

# Step 7: Summary
Write-Host "`n=============================================================="
Write-Host "Services Restarted with JaCoCo Monitoring!"
Write-Host "=============================================================="
Write-Host ""
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
Write-Host "Next Steps:"
Write-Host "  1. Run tests to collect coverage data:"
Write-Host "     python run_pipeline.py --services auth"
Write-Host "  2. Coverage data will be saved to:"
Write-Host "     $OUTPUT_DIR"
Write-Host "=============================================================="
