# engine.pattern_recorder.embedding

## Class: 

*Line: 16*

---

## Class: 

*Line: 24*

---

## Class: 

Embedding-based time series similarity.

Converts time series windows into feature vectors using:
1. Statistical features (mean, std, skew, kurtosis, etc.)
2. Spectral features (FFT coefficients)
3. Shape features (auto-correlation)

Then compares using cosine similarity for fast matching.

**Methods:** __init__, compute_embedding, _skewness, _kurtosis, _auto_correlation, _spectral_features, _linear_trend, cosine_similarity, search

*Line: 31*

---

## Function: 

*Line: 43*

---

## Function: 

Convert a time series window to embedding vector

*Line: 47*

---

## Function: 

Compute sample skewness

*Line: 88*

---

## Function: 

Compute excess kurtosis

*Line: 98*

---

## Function: 

Compute auto-correlation at specified lags

*Line: 108*

---

## Function: 

Compute FFT-based spectral features

*Line: 127*

---

## Function: 

Compute linear trend coefficient

*Line: 145*

---

## Function: 

Compute cosine similarity between two embeddings

*Line: 154*

---

## Function: 

Search for similar windows in database

*Line: 162*

---

