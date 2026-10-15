package com.checkout.payment.gateway;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.UUID;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class PaymentServiceTest {
  private final BankClient bank = mock(BankClient.class);
  private final PaymentService service = new PaymentService(bank);
  private final PaymentRequest request =
      new PaymentRequest("2222405343240001", 12, 2099, "GBP", 100L, "012");

  @ParameterizedTest
  @ValueSource(booleans = {true, false})
  void createAndRetrieve(boolean authorized) {
    when(bank.authorize(request)).thenReturn(authorized);
    Payment payment = service.create(request);
    assertThat(payment.status()).isEqualTo(authorized ? "Authorized" : "Declined");
    assertThat(payment.cardNumberLastFour()).isEqualTo("0001");
    assertThat(service.get(payment.id())).contains(payment);
    assertThat(service.get(UUID.randomUUID())).isEmpty();
    verify(bank).authorize(request);
  }

  @Test
  void bankFailureIsNotADeclinedPayment() {
    when(bank.authorize(request)).thenThrow(new BankException(503, "BankUnavailable"));
    assertThatThrownBy(() -> service.create(request)).isInstanceOf(BankException.class);
    verify(bank, times(1)).authorize(request);
  }

  @Test
  void concurrentCreatesHaveIndependentIdsAndAreRetrievable() {
    when(bank.authorize(request)).thenReturn(true);
    var payments = IntStream.range(0, 30).parallel()
        .mapToObj(i -> service.create(request)).toList();
    assertThat(payments.stream().map(Payment::id).distinct().count()).isEqualTo(30);
    payments.forEach(payment -> assertThat(service.get(payment.id())).contains(payment));
  }
}
