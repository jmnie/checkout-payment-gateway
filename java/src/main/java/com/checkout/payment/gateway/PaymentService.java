package com.checkout.payment.gateway;

import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

@Service
public class PaymentService {
  private final BankClient bank;
  private final ConcurrentHashMap<UUID, Payment> payments = new ConcurrentHashMap<>();

  public PaymentService(BankClient bank) {
    this.bank = bank;
  }

  public Payment create(PaymentRequest request) {
    boolean authorized = bank.authorize(request);
    String number = request.cardNumber();
    Payment payment = new Payment(UUID.randomUUID(), authorized ? "Authorized" : "Declined",
        number.substring(number.length() - 4), request.expiryMonth(), request.expiryYear(),
        request.currency(), request.amount());
    payments.put(payment.id(), payment);
    return payment;
  }

  public Optional<Payment> get(UUID id) {
    return Optional.ofNullable(payments.get(id));
  }
}
