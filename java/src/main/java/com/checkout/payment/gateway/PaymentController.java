package com.checkout.payment.gateway;

import jakarta.validation.Valid;
import java.net.URI;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PaymentController {
  private final PaymentService service;

  public PaymentController(PaymentService service) {
    this.service = service;
  }

  @PostMapping(value = "/payments", consumes = "application/json")
  ResponseEntity<Payment> create(@Valid @RequestBody PaymentRequest request) {
    Payment payment = service.create(request);
    return ResponseEntity.created(URI.create("/payments/" + payment.id())).body(payment);
  }

  @GetMapping("/payments/{id}")
  ResponseEntity<?> get(@PathVariable UUID id) {
    return service.get(id).<ResponseEntity<?>>map(ResponseEntity::ok)
        .orElseGet(() -> ResponseEntity.status(404).body(Map.of("code", "PaymentNotFound")));
  }

  @GetMapping("/health")
  Map<String, String> health() {
    return Map.of("status", "ok");
  }
}
