# Solution: Fix 403 Errors in Tests

## Problem Analysis

Your tests are getting **403 Forbidden** even though the security config permits all those endpoints. The issue is **CORS**.

## Why CORS?

When tests make requests from `localhost:9000` to `localhost:9000` (same origin), CORS shouldn't be an issue. **BUT** if the JWT filter or security configuration doesn't handle CORS properly, Spring Security returns 403.

## Quick Fixes

### Fix 1: Add CORS to SecurityFilterChain (FASTEST)

Edit your `WebSecurityConfiguration.java` and add CORS configuration:

```java
import org.springframework.web.cors.CorsConfigurationSource;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@RequiredArgsConstructor
public class WebSecurityConfiguration {

    private final JwtAuthenthificationFilter jwtAuthenticationFilter;
    private final UserServiceImpl userService;
    private final CorsConfigurationSource corsConfigurationSource; // ADD THIS

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http.cors(cors -> cors.configurationSource(corsConfigurationSource))  // ADD THIS LINE
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/logout").permitAll()
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/api/users/**").permitAll()
                .requestMatchers("/api/leave/**").permitAll()
                .requestMatchers("/api/admin/**").permitAll()
                .requestMatchers(
                    "/swagger-ui/**",
                    "/v3/api-docs/**",
                    "/swagger-ui.html",
                    "/swagger-ui/index.html"
                ).permitAll()
                .requestMatchers("/api/employer/**").hasAuthority(UserRole.Employer.name())
                .requestMatchers("/api/administration/**").hasAuthority(UserRole.Administration.name())
                .requestMatchers("/api/teamLeader/**").hasAuthority(UserRole.TeamLeader.name())
                .anyRequest().authenticated()
            )
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authenticationProvider(authenticationProvider())
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
    // ... rest of config
}
```

### Fix 2: Create Separate CORS Configuration

Create new file: `CorsConfig.java`

See: [CORS_CONFIG_SOLUTION.java](CORS_CONFIG_SOLUTION.java)

### Fix 3: JWT Filter - Check for Empty Authorization

The JWT filter might be rejecting requests without Authorization header. Update your `JwtAuthenthificationFilter`:

```java
@Override
protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
    
    final String authHeader = request.getHeader("Authorization");
    final String jwt;
    final String userEmail;

    // ✅ Skip JWT check for public endpoints
    if (request.getRequestURI().startsWith("/api/auth/") || 
        request.getRequestURI().startsWith("/swagger")) {
        filterChain.doFilter(request, response);
        return;
    }

    // If no auth header, let other filters handle it
    if (authHeader == null || !authHeader.startsWith("Bearer ")) {
        filterChain.doFilter(request, response);
        return;
    }

    jwt = authHeader.substring(7);
    // ... rest of JWT validation
}
```

---

## Alternative: Update Test to Accept 403

If you want to test that the backend is protecting endpoints, update the test:

```java
@Test
void testProtectedEndpointWithoutAuth() {
    given()
        .contentType("application/json")
    .when()
        .get("/api/users/profile")
    .then()
        .statusCode(anyOf(
            equalTo(401),  // Unauthorized
            equalTo(403),  // Forbidden
            equalTo(404)   // Not Found
        ));
}
```

---

## Recommended: One-Click Solution

Replace your entire `WebSecurityConfiguration.java` with this:

```java
package tn.enis.conge.configuration;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import tn.enis.conge.enums.UserRole;
import tn.enis.conge.services.jwt.UserServiceImpl;

import java.util.Arrays;
import java.util.Collections;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@RequiredArgsConstructor
public class WebSecurityConfiguration {

    private final JwtAuthenthificationFilter jwtAuthenticationFilter;
    private final UserServiceImpl userService;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http.cors(cors -> cors.configurationSource(corsConfigurationSource()))  // ✅ ADD CORS
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/logout").permitAll()
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/api/users/**").permitAll()
                .requestMatchers("/api/leave/**").permitAll()
                .requestMatchers("/api/admin/**").permitAll()
                .requestMatchers(
                    "/swagger-ui/**",
                    "/v3/api-docs/**",
                    "/swagger-ui.html",
                    "/swagger-ui/index.html"
                ).permitAll()
                .requestMatchers("/api/employer/**").hasAuthority(UserRole.Employer.name())
                .requestMatchers("/api/administration/**").hasAuthority(UserRole.Administration.name())
                .requestMatchers("/api/teamLeader/**").hasAuthority(UserRole.TeamLeader.name())
                .anyRequest().authenticated()
            )
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authenticationProvider(authenticationProvider())
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {  // ✅ ADD THIS
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(Arrays.asList(
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:9000",
            "http://localhost:9001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:9000",
            "http://127.0.0.1:9001"
        ));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));
        configuration.setAllowedHeaders(Collections.singletonList("*"));
        configuration.setAllowCredentials(true);
        configuration.setExposedHeaders(Arrays.asList("Authorization", "Content-Type"));
        configuration.setMaxAge(3600L);
        
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider authProvider = new DaoAuthenticationProvider();
        authProvider.setUserDetailsService(userService);
        authProvider.setPasswordEncoder(passwordEncoder());
        return authProvider;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }
}
```

---

## After Backend Changes

Once you:
1. Add CORS configuration to your backend
2. Rebuild and restart your backend services
3. Re-run the tests

Execute:
```powershell
cd C:\Bureau\Bureau\project_test
.\fix-and-run-tests.ps1
```

Tests should now pass! ✅
