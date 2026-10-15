package com.checkout.payment.gateway;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice
public class ApiErrors {
  @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
  ResponseEntity<?> rejected() {
    return ResponseEntity.badRequest().body(Map.of(
        "status", "Rejected", "message", "Invalid payment request"));
  }

  @ExceptionHandler(MethodArgumentTypeMismatchException.class)
  ResponseEntity<?> invalidId() {
    return ResponseEntity.badRequest().body(Map.of("code", "InvalidRequest"));
  }

  @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
  ResponseEntity<?> unsupportedMedia() {
    return ResponseEntity.status(415).body(Map.of("code", "UnsupportedMediaType"));
  }

  @ExceptionHandler(BankException.class)
  ResponseEntity<?> bankFailure(BankException error) {
    return ResponseEntity.status(error.status()).body(Map.of("code", error.getMessage()));
  }
}
