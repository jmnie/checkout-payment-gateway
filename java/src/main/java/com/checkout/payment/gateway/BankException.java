package com.checkout.payment.gateway;

public class BankException extends RuntimeException {
  private final int status;

  public BankException(int status, String code) {
    super(code);
    this.status = status;
  }

  public int status() {
    return status;
  }
}
