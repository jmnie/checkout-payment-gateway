package com.checkout.payment.gateway;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class BankClient {
  private static final Logger LOG = LoggerFactory.getLogger(BankClient.class);
  private final HttpClient client;
  private final ObjectMapper mapper;
  private final URI endpoint;
  private final Duration timeout;

  public BankClient(HttpClient client, ObjectMapper mapper, @Value("${bank.url}") String url,
      @Value("${bank.timeout-seconds}") double seconds) {
    this.client = client;
    this.mapper = mapper;
    this.endpoint = URI.create(url + "/payments");
    this.timeout = Duration.ofMillis((long) (seconds * 1000));
  }

  public boolean authorize(PaymentRequest payment) {
    long started = System.nanoTime();
    String outcome = "error";
    try {
      HttpRequest request = HttpRequest.newBuilder(endpoint).timeout(timeout)
          .header("Content-Type", "application/json")
          .POST(HttpRequest.BodyPublishers.ofString(serialize(payment))).build();
      HttpResponse<String> response;
      try {
        response = client.send(request, HttpResponse.BodyHandlers.ofString());
      } catch (HttpTimeoutException e) {
        throw new BankException(504, "BankTimeout");
      } catch (IOException e) {
        throw new BankException(503, "BankUnavailable");
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new BankException(503, "BankUnavailable");
      }
      if (response.statusCode() == 503) {
        throw new BankException(503, "BankUnavailable");
      }
      if (response.statusCode() != 200) {
        throw new BankException(502, "BankInvalidResponse");
      }
      JsonNode data;
      try {
        data = mapper.readTree(response.body());
      } catch (JsonProcessingException e) {
        throw new BankException(502, "BankInvalidResponse");
      }
      if (data == null || !data.path("authorized").isBoolean()) {
        throw new BankException(502, "BankInvalidResponse");
      }
      boolean authorized = data.get("authorized").booleanValue();
      outcome = authorized ? "Authorized" : "Declined";
      return authorized;
    } catch (BankException e) {
      outcome = e.getMessage();
      throw e;
    } finally {
      LOG.info("{\"event\":\"bank_call\",\"request_id\":\"{}\","
              + "\"outcome\":\"{}\",\"duration_ms\":{}}",
          MDC.get("request_id"), outcome, (System.nanoTime() - started) / 1_000_000.0);
    }
  }

  private String serialize(PaymentRequest payment) {
    try {
      return mapper.writeValueAsString(Map.of(
          "card_number", payment.cardNumber(),
          "expiry_date", "%02d/%04d".formatted(payment.expiryMonth(), payment.expiryYear()),
          "currency", payment.currency(), "amount", payment.amount(), "cvv", payment.cvv()));
    } catch (JsonProcessingException e) {
      // This map only contains validated strings and integers; failure is a programming error.
      throw new IllegalStateException("Could not serialize bank request", e);
    }
  }
}
