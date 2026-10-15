package com.checkout.payment.gateway;

import java.util.UUID;

public record Payment(UUID id, String status, String cardNumberLastFour,
                      int expiryMonth, int expiryYear, String currency, long amount) {
}
