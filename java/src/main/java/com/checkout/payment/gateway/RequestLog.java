package com.checkout.payment.gateway;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerMapping;

@Component
public class RequestLog extends OncePerRequestFilter {
  private static final Logger LOG = LoggerFactory.getLogger(RequestLog.class);

  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    String id = UUID.randomUUID().toString();
    MDC.put("request_id", id);
    response.setHeader("X-Request-Id", id);
    long started = System.nanoTime();
    int status = 500;
    try {
      chain.doFilter(request, response);
      status = response.getStatus();
    } finally {
      Object route = request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
      LOG.info("{\"event\":\"http_request\",\"request_id\":\"{}\",\"method\":\"{}\","
              + "\"route\":\"{}\",\"status\":{},\"duration_ms\":{}}",
          id, request.getMethod(), route == null ? "unmatched" : route, status,
          (System.nanoTime() - started) / 1_000_000.0);
      MDC.remove("request_id");
    }
  }
}
