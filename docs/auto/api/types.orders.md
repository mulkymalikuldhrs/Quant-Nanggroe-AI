# types.orders

## Class: 

Order type classification.

*Line: 16*

---

## Class: 

Order direction.

*Line: 27*

---

## Class: 

Order lifecycle status.

*Line: 33*

---

## Class: 

Base order type with all common fields.

Every order in the system must have these fields regardless of broker.
Orders are validated by the risk engine before submission.

*Line: 45*

---

## Class: 

Market order - executes immediately at current market price.

*Line: 76*

---

## Class: 

Limit order - executes at specified price or better.

*Line: 81*

---

## Class: 

Stop order - triggers market order when stop price is reached.

*Line: 87*

---

## Class: 

Stop-limit order - triggers limit order when stop price is reached.

*Line: 93*

---

