package com.checkout.payment.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.time.YearMonth;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

class PaymentRequestTest {
  private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

  @Test
  void preservesLeadingZerosAndAcceptsBounds() {
    for (String card : new String[]{"0".repeat(13) + "1", "1".repeat(19)}) {
      for (String currency : new String[]{"USD", "EUR", "GBP"}) {
        PaymentRequest request =
            new PaymentRequest(card, 1, 2099, currency, Long.MAX_VALUE, "0000");
        assertThat(validator.validate(request)).isEmpty();
        assertThat(request.toString()).doesNotContain(card).doesNotContain("0000");
      }
    }
  }

  @Test
  void expiryMustBeAfterCurrentMonth() {
    YearMonth current = YearMonth.now(ZoneOffset.UTC);
    assertThat(validator.validate(requestFor(current))).isNotEmpty();
    assertThat(validator.validate(requestFor(current.minusMonths(1)))).isNotEmpty();
    assertThat(validator.validate(requestFor(current.plusMonths(1)))).isEmpty();
  }

  private PaymentRequest requestFor(YearMonth expiry) {
    return new PaymentRequest("2222405343240001", expiry.getMonthValue(), expiry.getYear(),
        "GBP", 100L, "012");
  }
}
