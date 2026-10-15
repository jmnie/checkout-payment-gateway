package com.checkout.payment.gateway;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.util.UUID;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ExtendWith(OutputCaptureExtension.class)
class PaymentApiTest {
  @Autowired MockMvc mvc;
  @Autowired ObjectMapper mapper;
  @MockitoBean BankClient bank;

  private String payload() throws Exception {
    return java.nio.file.Files.readString(Path.of("../tests/payment.json"));
  }

  static Stream<Arguments> invalidRequests() throws Exception {
    JsonNode rows = new ObjectMapper().readTree(Path.of("../tests/invalid_requests.json").toFile());
    return StreamSupport.stream(rows.spliterator(), false)
        .map(row -> Arguments.of(
            row.get("name").asText(), row.get("request").toString()));
  }

  @ParameterizedTest(name = "{0}")
  @MethodSource("invalidRequests")
  void invalidInputIsRejectedBeforeBankCall(String name, String body) throws Exception {
    mvc.perform(post("/payments").contentType("application/json").content(body))
        .andExpect(status().isBadRequest())
        .andExpect(content().json(
            "{\"status\":\"Rejected\",\"message\":\"Invalid payment request\"}"));
    verifyNoInteractions(bank);
  }

  @Test
  void createAndGetBothDecisions() throws Exception {
    for (boolean authorized : new boolean[]{true, false}) {
      when(bank.authorize(any())).thenReturn(authorized);
      var response = mvc.perform(post("/payments")
              .contentType("application/json").content(payload()))
          .andExpect(status().isCreated())
          .andExpect(jsonPath("$.status").value(authorized ? "Authorized" : "Declined"))
          .andExpect(jsonPath("$.card_number_last_four").value("0001"))
          .andExpect(jsonPath("$.card_number").doesNotExist())
          .andExpect(jsonPath("$.cvv").doesNotExist())
          .andReturn().getResponse();
      String location = response.getHeader("Location");
      var retrieved = mvc.perform(get(location))
          .andExpect(status().isOk()).andReturn().getResponse();
      assertThat(mapper.readTree(retrieved.getContentAsString()))
          .isEqualTo(mapper.readTree(response.getContentAsString()));
    }
  }

  @ParameterizedTest
  @CsvSource({"502,BankInvalidResponse", "503,BankUnavailable", "504,BankTimeout"})
  void bankErrorsAreTechnicalErrors(int status, String code) throws Exception {
    doThrow(new BankException(status, code)).when(bank).authorize(any());
    mvc.perform(post("/payments").contentType("application/json").content(payload()))
        .andExpect(status().is(status)).andExpect(jsonPath("$.code").value(code))
        .andExpect(jsonPath("$.status").doesNotExist())
        .andExpect(header().doesNotExist("Location"));
  }

  @Test
  void rejectsMalformedJsonAndWrongContentType() throws Exception {
    for (String body : new String[]{"{", "null", "[]", "{} {}"}) {
      mvc.perform(post("/payments").contentType("application/json").content(body))
          .andExpect(status().isBadRequest());
    }
    mvc.perform(post("/payments").content("{}")).andExpect(status().isUnsupportedMediaType());
    verifyNoInteractions(bank);
  }

  @Test
  void missingAndInvalidIds() throws Exception {
    mvc.perform(get("/payments/" + UUID.randomUUID())).andExpect(status().isNotFound())
        .andExpect(jsonPath("$.code").value("PaymentNotFound"));
    mvc.perform(get("/payments/not-a-uuid")).andExpect(status().isBadRequest());
  }

  @Test
  void unexpectedFailureIsLoggedAs500(CapturedOutput output) throws Exception {
    when(bank.authorize(any())).thenThrow(new IllegalStateException("unexpected failure"));
    assertThatThrownBy(() -> mvc.perform(post("/payments")
        .contentType("application/json").content(payload())))
        .hasRootCauseInstanceOf(IllegalStateException.class);
    assertThat(output.getOut()).contains("\"status\":500");
  }

  @Test
  void logsAreCorrelatedAndRedacted(CapturedOutput output) throws Exception {
    when(bank.authorize(any())).thenReturn(true);
    var response = mvc.perform(post("/payments").contentType("application/json").content(payload()))
        .andExpect(status().isCreated()).andReturn().getResponse();
    String id = response.getHeader("X-Request-Id");
    UUID.fromString(id);
    var second = mvc.perform(get("/health")).andExpect(status().isOk()).andReturn().getResponse();
    assertThat(second.getHeader("X-Request-Id")).isNotEqualTo(id);
    assertThat(output.getAll()).contains(id).contains("duration_ms")
        .doesNotContain("2222405343240001").doesNotContain("\"cvv\"");
  }
}
