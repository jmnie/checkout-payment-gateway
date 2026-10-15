package com.checkout.payment.gateway;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.json.JsonTest;

@JsonTest
class BankClientTest {
  @Autowired ObjectMapper mapper;
  private HttpServer server;
  private BankClient bank;
  private final PaymentRequest payment =
      new PaymentRequest("2222405343240001", 1, 2099, "GBP", 100L, "012");

  @BeforeEach
  void start() throws Exception {
    server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.start();
    bank = new BankClient(HttpClient.newHttpClient(), mapper,
        "http://127.0.0.1:" + server.getAddress().getPort(), 2);
  }

  @AfterEach
  void stop() {
    server.stop(0);
  }

  @ParameterizedTest
  @CsvSource({"true", "false"})
  void serializesBankContractAndReadsDecision(boolean authorized) {
    server.createContext("/payments", exchange -> {
      var body = mapper.readTree(exchange.getRequestBody());
      assertThat(exchange.getRequestMethod()).isEqualTo("POST");
      assertThat(body.size()).isEqualTo(5);
      assertThat(body.get("card_number").asText()).isEqualTo(payment.cardNumber());
      assertThat(body.get("expiry_date").asText()).isEqualTo("01/2099");
      assertThat(body.get("currency").asText()).isEqualTo("GBP");
      assertThat(body.get("amount").asLong()).isEqualTo(100);
      assertThat(body.get("cvv").asText()).isEqualTo("012");
      byte[] bytes = ("{\"authorized\":" + authorized + "}").getBytes(StandardCharsets.UTF_8);
      exchange.sendResponseHeaders(200, bytes.length);
      exchange.getResponseBody().write(bytes);
      exchange.close();
    });
    assertThat(bank.authorize(payment)).isEqualTo(authorized);
  }

  @ParameterizedTest
  @CsvSource(value = {
      "503|{}|503|BankUnavailable", "400|{}|502|BankInvalidResponse",
      "500|{}|502|BankInvalidResponse", "302|{}|502|BankInvalidResponse",
      "200|broken|502|BankInvalidResponse", "200|{}|502|BankInvalidResponse",
      "200|{\"authorized\":true} {}|502|BankInvalidResponse",
      "200|null|502|BankInvalidResponse", "200|[]|502|BankInvalidResponse",
      "200|{\"authorized\":\"false\"}|502|BankInvalidResponse",
      "200|{\"authorized\":1}|502|BankInvalidResponse"
  }, delimiter = '|')
  void bankFailures(int upstreamStatus, String body, int expected, String code) {
    AtomicInteger calls = new AtomicInteger();
    server.createContext("/payments", exchange -> {
      calls.incrementAndGet();
      byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
      exchange.sendResponseHeaders(upstreamStatus, bytes.length);
      exchange.getResponseBody().write(bytes);
      exchange.close();
    });
    assertThatThrownBy(() -> bank.authorize(payment))
        .isInstanceOfSatisfying(BankException.class, e -> {
          assertThat(e.status()).isEqualTo(expected);
          assertThat(e.getMessage()).isEqualTo(code);
        });
    assertThat(calls.get()).isEqualTo(1);
  }

  @Test
  void timesOut() {
    bank = new BankClient(HttpClient.newHttpClient(), mapper,
        "http://127.0.0.1:" + server.getAddress().getPort(), 0.1);
    server.createContext("/payments", exchange -> {
      try {
        Thread.sleep(350);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
      }
      exchange.close();
    });
    assertThatThrownBy(() -> bank.authorize(payment)).isInstanceOfSatisfying(BankException.class,
        e -> assertThat(e.status()).isEqualTo(504));
  }

  @Test
  void unavailableConnection() {
    server.stop(0);
    assertThatThrownBy(() -> bank.authorize(payment)).isInstanceOfSatisfying(BankException.class,
        e -> assertThat(e.status()).isEqualTo(503));
  }
}
