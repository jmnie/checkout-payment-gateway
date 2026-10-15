package com.checkout.payment.gateway;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.time.YearMonth;
import java.time.ZoneOffset;

public record PaymentRequest(
    @NotNull @Pattern(regexp = "[0-9]{14,19}") String cardNumber,
    @NotNull @Min(1) @Max(12) Integer expiryMonth,
    @NotNull @Min(1) @Max(9999) Integer expiryYear,
    @NotNull @Pattern(regexp = "USD|GBP|EUR") String currency,
    @NotNull @Min(1) Long amount,
    @NotNull @Pattern(regexp = "[0-9]{3,4}") String cvv) {

  @AssertTrue
  @JsonIgnore
  public boolean isExpiryInFuture() {
    // Leave missing/out-of-range values to the field constraints.
    if (expiryMonth == null || expiryYear == null || expiryMonth < 1 || expiryMonth > 12
        || expiryYear < 1 || expiryYear > 9999) {
      return true;
    }
    return YearMonth.of(expiryYear, expiryMonth).isAfter(YearMonth.now(ZoneOffset.UTC));
  }

  @Override
  public String toString() {
    return "PaymentRequest[redacted]";
  }
}
